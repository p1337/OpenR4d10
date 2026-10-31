/* OpenR4d10 native Whisplay boot player.
 * Controller setup derived from PiSugar/Whisplay (Apache-2.0),
 * b2ccecab528caf939f0e3a900547cd094029f13e/runtime/whisplay.py.
 * Native SPI, Linux GPIO v2, zlib only. No Python or video decoder at boot.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <linux/gpio.h>
#include <linux/spi/spidev.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include <zlib.h>

enum { WIDTH=240, HEIGHT=280, FRAME_BYTES=134400, MAX_FRAMES=4096 };
static const char *runtime_dir="/run/openr4d10-boot";
static const char *marker="/run/openr4d10-boot/panel.ready";
static const char *release_file="/run/openr4d10-boot/release";
static const char *panel_id="ST7789-240x280-C0-y20\n";
static volatile sig_atomic_t stop_requested=0;
static int spi_fd=-1, lines_fd=-1, lock_fd=-1;
static uint32_t speed_hz=32000000;
static bool backlight_queued=false;

typedef struct {
    unsigned char *data;
    size_t size;
    uint32_t fps_num, fps_den, count, loop_start;
    size_t offsets[MAX_FRAMES];
    uint32_t lengths[MAX_FRAMES], crcs[MAX_FRAMES];
} Movie;

static void fail(const char *message) { perror(message); exit(EXIT_FAILURE); }
static void invalid(const char *message) { fprintf(stderr,"boot asset: %s\n",message); exit(EXIT_FAILURE); }
static void signal_stop(int sig) { (void)sig; stop_requested=1; }
static uint32_t le32(const unsigned char *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static uint16_t le16(const unsigned char *p) { return (uint16_t)(p[0]|(uint16_t)p[1]<<8); }
static int64_t now_ns(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t)) fail("clock_gettime");
    return (int64_t)t.tv_sec*1000000000+t.tv_nsec;
}
static void pause_ms(unsigned ms) {
    struct timespec t={.tv_sec=ms/1000,.tv_nsec=(long)(ms%1000)*1000000};
    while(nanosleep(&t,&t)&&errno==EINTR&&!stop_requested) {}
}
static void cleanup(void) {
    /* Deliberately do not clear display RAM or change the kernel-owned backlight. */
    if(spi_fd>=0) close(spi_fd);
    if(lines_fd>=0) close(lines_fd);
    if(lock_fd>=0) close(lock_fd);
}
static void queue_backlight(unsigned brightness) {
    const char *dir="/run/openr4d10-backlight";
    const char *request="/run/openr4d10-backlight/brightness.request";
    char temporary[160];
    if(brightness>100) invalid("invalid backlight brightness");
    int n=snprintf(temporary,sizeof(temporary),"%s/.brightness.%ld",dir,(long)getpid());
    if(n<0||(size_t)n>=sizeof(temporary)) invalid("backlight request path too long");
    int fd=open(temporary,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,0600);
    if(fd<0) fail("open backlight request");
    char value[8];
    n=snprintf(value,sizeof(value),"%u\n",brightness);
    if(n<0||write(fd,value,(size_t)n)!=n||fsync(fd)||close(fd)) fail("write backlight request");
    if(rename(temporary,request)) fail("publish backlight request");
}
static void movie_open(Movie *m,const char *path) {
    int fd=open(path,O_RDONLY|O_CLOEXEC);
    if(fd<0) fail(path);
    struct stat st;
    if(fstat(fd,&st)) fail("fstat asset");
    if(st.st_size<32||st.st_size>512*1024*1024) invalid("invalid file size");
    m->size=(size_t)st.st_size;
    m->data=mmap(NULL,m->size,PROT_READ,MAP_PRIVATE,fd,0);
    close(fd);
    if(m->data==MAP_FAILED) fail("mmap asset");
    const unsigned char *h=m->data;
    if(memcmp(h,"OR4BOOT1",8)||le16(h+8)!=WIDTH||le16(h+10)!=HEIGHT) invalid("wrong format or display dimensions");
    m->fps_num=le32(h+12); m->fps_den=le32(h+16);
    m->count=le32(h+20); m->loop_start=le32(h+24);
    if(!m->fps_num||!m->fps_den||m->fps_den>1001||m->fps_num>60*m->fps_den||
       !m->count||m->count>MAX_FRAMES||m->loop_start>=m->count||le32(h+28)!=FRAME_BYTES)
        invalid("invalid timing or frame count");
    size_t pos=32;
    for(uint32_t i=0;i<m->count;i++) {
        if(pos>m->size||m->size-pos<8) invalid("truncated frame header");
        uint32_t n=le32(m->data+pos);
        m->crcs[i]=le32(m->data+pos+4); pos+=8;
        if(!n||n>compressBound(FRAME_BYTES)||n>m->size-pos) invalid("invalid compressed frame size");
        m->offsets[i]=pos; m->lengths[i]=n; pos+=n;
    }
    if(pos!=m->size) invalid("unexpected trailing data");
}
static void decode(const Movie *m,uint32_t i,unsigned char *frame) {
    uLongf size=FRAME_BYTES;
    if(uncompress(frame,&size,m->data+m->offsets[i],m->lengths[i])!=Z_OK||size!=FRAME_BYTES)
        invalid("zlib decode failure");
    if((uint32_t)crc32(0,frame,FRAME_BYTES)!=m->crcs[i]) invalid("frame CRC mismatch");
}
static void gpio_value(unsigned index,bool high) {
    struct gpio_v2_line_values values={.bits=high?(UINT64_C(1)<<index):0,.mask=UINT64_C(1)<<index};
    if(ioctl(lines_fd,GPIO_V2_LINE_SET_VALUES_IOCTL,&values)) fail("GPIO set");
}
static void spi_bytes(const unsigned char *data,size_t n) {
    while(n) {
        size_t chunk=n>4096?4096:n;
        ssize_t written=write(spi_fd,data,chunk);
        if(written<0&&errno==EINTR&&!stop_requested) continue;
        if(written!=(ssize_t)chunk) fail("SPI write");
        data+=chunk; n-=chunk;
    }
}
static void command(unsigned char cmd,const unsigned char *data,size_t n) {
    gpio_value(1,false); spi_bytes(&cmd,1);
    gpio_value(1,true); if(n) spi_bytes(data,n);
}
#define CMD(c,...) do { const unsigned char args_[]={__VA_ARGS__}; command(c,args_,sizeof(args_)); } while(0)
static void init_panel(void) {
    gpio_value(0,true); pause_ms(100);
    gpio_value(0,false); pause_ms(100);
    gpio_value(0,true); pause_ms(120);
    command(0x11,NULL,0); pause_ms(120);
    CMD(0x36,0xC0); CMD(0x3A,0x05);
    CMD(0xB2,0x0C,0x0C,0x00,0x33,0x33); CMD(0xB7,0x35); CMD(0xBB,0x32);
    CMD(0xC2,0x01); CMD(0xC3,0x15); CMD(0xC4,0x20); CMD(0xC6,0x0F); CMD(0xD0,0xA4,0xA1);
    CMD(0xE0,0xD0,0x08,0x0E,0x09,0x09,0x05,0x31,0x33,0x48,0x17,0x14,0x15,0x31,0x34);
    CMD(0xE1,0xD0,0x08,0x0E,0x09,0x09,0x15,0x31,0x33,0x48,0x17,0x14,0x15,0x31,0x34);
    command(0x21,NULL,0); command(0x29,NULL,0);
}
static bool already_initialized(void) {
    char text[64]={0};
    FILE *f=fopen(marker,"r");
    if(!f) return false;
    size_t n=fread(text,1,sizeof(text)-1,f); fclose(f);
    return n==strlen(panel_id)&&!strcmp(text,panel_id);
}
static void hardware_open(void) {
    char model[256]={0};
    FILE *f=fopen("/proc/device-tree/model","r");
    if(!f) invalid("Pi Zero 2 W hardware required; --verify works on development hosts");
    size_t model_size=fread(model,1,sizeof(model)-1,f); fclose(f);
    if(!model_size) invalid("empty Raspberry Pi model");
    if(!strstr(model,"Raspberry Pi Zero 2")) invalid("only the verified Pi Zero 2 W pin map is enabled");
    if(mkdir(runtime_dir,0770)&&errno!=EEXIST) fail("runtime directory");
    lock_fd=open("/run/openr4d10-boot/display.lock",O_CREAT|O_RDWR|O_CLOEXEC|O_NOFOLLOW,0660);
    if(lock_fd<0||flock(lock_fd,LOCK_EX|LOCK_NB)) fail("display owner lock");
    if(fchown(lock_fd,(uid_t)-1,getgid())||fchmod(lock_fd,0660)) fail("display lock permissions");
    bool initialized=already_initialized();
    int chip=-1;
    for(int retry=0;retry<100&&!stop_requested;retry++) {
        chip=open("/dev/gpiochip0",O_RDONLY|O_CLOEXEC);
        spi_fd=open("/dev/spidev0.0",O_RDWR|O_CLOEXEC);
        if(chip>=0&&spi_fd>=0) break;
        if(chip>=0) close(chip);
        if(spi_fd>=0) close(spi_fd);
        chip=-1; spi_fd=-1; pause_ms(20);
    }
    if(chip<0||spi_fd<0) fail("Whisplay SPI/GPIO devices not ready");
    struct gpiochip_info chip_info={0};
    if(ioctl(chip,GPIO_GET_CHIPINFO_IOCTL,&chip_info)) fail("GPIO chip info");
    if(!strstr(chip_info.label,"bcm2835")) invalid("unexpected GPIO controller; refusing guessed pin mapping");
    struct gpio_v2_line_request req={0};
    req.offsets[0]=4; req.offsets[1]=27; req.num_lines=2;
    strcpy(req.consumer,"openr4d10-boot"); req.config.flags=GPIO_V2_LINE_FLAG_OUTPUT;
    req.config.num_attrs=1;
    req.config.attrs[0].attr.id=GPIO_V2_LINE_ATTR_ID_OUTPUT_VALUES;
    req.config.attrs[0].attr.values=3;
    req.config.attrs[0].mask=3;
    if(ioctl(chip,GPIO_V2_GET_LINE_IOCTL,&req)) fail("Whisplay GPIO request; another owner may be active");
    lines_fd=req.fd; close(chip);
    uint8_t mode=SPI_MODE_0,bits=8;
    if(ioctl(spi_fd,SPI_IOC_WR_MODE,&mode)||ioctl(spi_fd,SPI_IOC_WR_BITS_PER_WORD,&bits)||
       ioctl(spi_fd,SPI_IOC_WR_MAX_SPEED_HZ,&speed_hz)) fail("SPI configuration");
    if(!initialized) init_panel();
}
static void show_frame(const unsigned char *frame) {
    CMD(0x2A,0x00,0x00,0x00,0xEF);
    CMD(0x2B,0x00,0x14,0x01,0x2B); /* rows 20 through 299 inclusive */
    command(0x2C,NULL,0); spi_bytes(frame,FRAME_BYTES);
    if(!backlight_queued) {
        /* The kernel PWM kept the active-low backlight off until this frame. */
        queue_backlight(100);
        backlight_queued=true;
    }
}
int main(int argc,char **argv) {
    bool verify=false,still=false,loop=false;
    unsigned benchmark=1;
    const char *path=NULL;
    const char *env_speed=getenv("OPENR4D10_SPI_HZ");
    if(env_speed) {
        char *end; unsigned long n=strtoul(env_speed,&end,10);
        if(*end||n<1000000||n>100000000) invalid("invalid SPI frequency");
        speed_hz=(uint32_t)n;
    }
    for(int i=1;i<argc;i++) {
        if(!strcmp(argv[i],"--verify")) verify=true;
        else if(!strcmp(argv[i],"--still")) still=true;
        else if(!strcmp(argv[i],"--loop")) loop=true;
        else if(!strcmp(argv[i],"--benchmark")&&i+1<argc) {
            char *end; unsigned long n=strtoul(argv[++i],&end,10);
            if(*end||!n||n>10000) invalid("invalid benchmark count");
            benchmark=(unsigned)n; verify=true;
        } else if(argv[i][0]=='-') invalid("usage: openr4d10-boot [--verify] [--benchmark N] [--still|--loop] asset.opb");
        else if(path) invalid("only one asset path is allowed");
        else path=argv[i];
    }
    if(!path) invalid("asset path required");
    Movie movie={0}; movie_open(&movie,path);
    unsigned char *frame=malloc(FRAME_BYTES);
    if(!frame) fail("allocate frame");
    if(verify) {
        int64_t start=now_ns();
        for(unsigned pass=0;pass<benchmark;pass++)
            for(uint32_t i=0;i<movie.count;i++) decode(&movie,i,frame);
        double seconds=(double)(now_ns()-start)/1e9;
        printf("verified=%u frames, %dx%d RGB565, fps=%u/%u, loop_start=%u, compressed=%zu bytes\n",
               movie.count,WIDTH,HEIGHT,movie.fps_num,movie.fps_den,movie.loop_start,movie.size);
        printf("host_decode_only=%.1f frames/s, passes=%u, seconds=%.6f; NOT a Pi/SPI benchmark\n",
               movie.count*(double)benchmark/seconds,benchmark,seconds);
        free(frame); munmap(movie.data,movie.size); return 0;
    }
    atexit(cleanup); signal(SIGTERM,signal_stop); signal(SIGINT,signal_stop);
    hardware_open();
    int64_t start=now_ns();
    uint64_t tick=0,dropped=0;
    int64_t period=(int64_t)1000000000*movie.fps_den/movie.fps_num;
    while(!stop_requested) {
        if(access(release_file,F_OK)==0) break;
        uint32_t index;
        if(tick<movie.count) index=(uint32_t)tick;
        else if(loop) index=movie.loop_start+(uint32_t)((tick-movie.count)%(movie.count-movie.loop_start));
        else break;
        decode(&movie,index,frame); show_frame(frame);
        if(!tick) {
            int marker_fd=open(marker,O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC|O_NOFOLLOW,0660);
            if(marker_fd>=0) {
                size_t n=strlen(panel_id);
                if(write(marker_fd,panel_id,n)!=(ssize_t)n) perror("panel marker write");
                close(marker_fd);
            }
            fprintf(stderr,"openr4d10 first frame at kernel monotonic %.3f s; SPI target=%u\n",now_ns()/1e9,speed_hz);
        }
        if(still) break;
        tick++;
        int64_t deadline=start+(int64_t)tick*period,now=now_ns();
        if(now>deadline+period) {
            uint64_t next=(uint64_t)((now-start)/period);
            dropped+=next-tick; tick=next; deadline=start+(int64_t)tick*period;
        }
        struct timespec target={.tv_sec=deadline/1000000000,.tv_nsec=deadline%1000000000};
        int result;
        while((result=clock_nanosleep(CLOCK_MONOTONIC,TIMER_ABSTIME,&target,NULL))==EINTR&&!stop_requested) {}
        if(result&&result!=EINTR) { errno=result; fail("frame pacing"); }
    }
    fprintf(stderr,"openr4d10 display released; late_frames_dropped=%" PRIu64 "\n",dropped);
    free(frame); munmap(movie.data,movie.size); return 0;
}
