"use strict";

(() => {
  const ENDPOINT = "wss://hose.brandmeister.network/spotter/?token=test%3Atest";
  const PROTOCOL = "spotter";

  function encodeUnsigned(value) {
    if (value <= 0x7f) return [value];
    if (value <= 0xff) return [0xcc, value];
    if (value <= 0xffff) return [0xcd, value >>> 8, value & 0xff];
    return [
      0xce,
      (value >>> 24) & 0xff,
      (value >>> 16) & 0xff,
      (value >>> 8) & 0xff,
      value & 0xff,
    ];
  }

  function groupMessage(type, talkgroups) {
    const values = talkgroups.flatMap(encodeUnsigned);
    return new Uint8Array([0x92, type, 0x90 + talkgroups.length, ...values]);
  }

  function singleMessage(type) {
    return new Uint8Array([0x91, type]);
  }

  function decodeMessagePack(payload) {
    const bytes = payload instanceof Uint8Array ? payload : new Uint8Array(payload);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const textDecoder = new TextDecoder("utf-8", { fatal: false });
    let offset = 0;

    const take = (length) => {
      if (!Number.isInteger(length) || length < 0 || length > 1024 * 1024) {
        throw new Error("invalid MessagePack length");
      }
      if (offset + length > bytes.length) throw new Error("truncated MessagePack value");
      const result = bytes.subarray(offset, offset + length);
      offset += length;
      return result;
    };
    const number = (method, length) => {
      if (offset + length > bytes.length) throw new Error("truncated MessagePack number");
      const result = view[method](offset);
      offset += length;
      return result;
    };
    const read = (depth = 0) => {
      if (depth > 16 || offset >= bytes.length) throw new Error("invalid MessagePack value");
      const marker = bytes[offset++];
      if (marker <= 0x7f) return marker;
      if (marker >= 0xe0) return marker - 0x100;
      if ((marker & 0xf0) === 0x90) {
        return Array.from({ length: marker & 0x0f }, () => read(depth + 1));
      }
      if ((marker & 0xe0) === 0xa0) return textDecoder.decode(take(marker & 0x1f));
      if (marker === 0xc0) return null;
      if (marker === 0xc2) return false;
      if (marker === 0xc3) return true;
      if (marker === 0xc4) return take(number("getUint8", 1));
      if (marker === 0xc5) return take(number("getUint16", 2));
      if (marker === 0xc6) return take(number("getUint32", 4));
      if (marker === 0xca) return number("getFloat32", 4);
      if (marker === 0xcb) return number("getFloat64", 8);
      if (marker === 0xcc) return number("getUint8", 1);
      if (marker === 0xcd) return number("getUint16", 2);
      if (marker === 0xce) return number("getUint32", 4);
      if (marker === 0xd0) return number("getInt8", 1);
      if (marker === 0xd1) return number("getInt16", 2);
      if (marker === 0xd2) return number("getInt32", 4);
      if (marker === 0xd9) return textDecoder.decode(take(number("getUint8", 1)));
      if (marker === 0xda) return textDecoder.decode(take(number("getUint16", 2)));
      if (marker === 0xdc) {
        const length = number("getUint16", 2);
        return Array.from({ length }, () => read(depth + 1));
      }
      throw new Error(`unsupported MessagePack marker 0x${marker.toString(16)}`);
    };

    return read();
  }

  function muLawSample(value) {
    const sample = (~value) & 0xff;
    const sign = sample & 0x80;
    const exponent = (sample >>> 4) & 0x07;
    const mantissa = sample & 0x0f;
    const base = [0, 132, 396, 924, 1980, 4092, 8316, 16764][exponent];
    const magnitude = base + (mantissa << (exponent + 3));
    return (sign ? -magnitude : magnitude) / 32768;
  }

  class HoseLineReceiver {
    constructor(onState) {
      this.onState = onState;
      this.socket = null;
      this.context = null;
      this.talkgroups = [];
      this.nextAudioTime = 0;
      this.sources = new Set();
      this.generation = 0;
      this.call = {};
    }

    state(status, extra = {}) {
      this.onState({ status, talkgroups: [...this.talkgroups], ...extra });
    }

    async connect(talkgroups) {
      this.disconnect(false);
      this.talkgroups = [...talkgroups];
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) throw new Error("Web Audio is unavailable");
      this.context = new AudioContext();
      await this.context.resume();
      const generation = ++this.generation;
      this.state("connecting");
      const socket = new WebSocket(ENDPOINT, PROTOCOL);
      socket.binaryType = "arraybuffer";
      this.socket = socket;
      socket.addEventListener("open", () => {
        if (generation !== this.generation) return;
        socket.send(groupMessage(1, talkgroups));
        this.state("connected");
      });
      socket.addEventListener("message", (event) => {
        if (generation !== this.generation) return;
        try {
          this.receive(decodeMessagePack(event.data));
        } catch (error) {
          console.warn("Ignored malformed HoseLine packet", error);
        }
      });
      socket.addEventListener("error", () => {
        if (generation === this.generation) this.state("error");
      });
      socket.addEventListener("close", () => {
        if (generation === this.generation) this.state("closed");
      });
    }

    receive(message) {
      if (!Array.isArray(message)) return;
      if (message[0] === 11) {
        this.call = { source: message[2], destination: message[3], alias: "" };
        this.state("call", this.call);
      } else if (message[0] === 13) {
        this.call = {};
        this.state("connected");
      } else if (message[0] === 20 && message[1] instanceof Uint8Array) {
        this.play(message[1]);
      } else if (message[0] === 21) {
        this.call.alias = String(message[1] || "");
        this.state("call", this.call);
      } else if (message[0] === 80) {
        this.state("error");
      }
    }

    play(packet) {
      if (!this.context || this.context.state === "closed" || packet.length === 0) return;
      const buffer = this.context.createBuffer(1, packet.length, 8000);
      const channel = buffer.getChannelData(0);
      for (let index = 0; index < packet.length; index += 1) {
        channel[index] = muLawSample(packet[index]) * 0.8;
      }
      const source = this.context.createBufferSource();
      source.buffer = buffer;
      source.connect(this.context.destination);
      const earliest = this.context.currentTime + 0.04;
      if (this.nextAudioTime < earliest || this.nextAudioTime > earliest + 2) {
        this.nextAudioTime = earliest;
      }
      source.start(this.nextAudioTime);
      this.nextAudioTime += buffer.duration;
      this.sources.add(source);
      source.addEventListener("ended", () => this.sources.delete(source), { once: true });
    }

    disconnect(notify = true) {
      this.generation += 1;
      const socket = this.socket;
      this.socket = null;
      if (socket && socket.readyState === WebSocket.OPEN && this.talkgroups.length) {
        socket.send(groupMessage(2, this.talkgroups));
        socket.send(singleMessage(12));
      }
      if (socket) socket.close();
      for (const source of this.sources) {
        try { source.stop(); } catch (_error) { /* already stopped */ }
      }
      this.sources.clear();
      if (this.context) this.context.close().catch(() => {});
      this.context = null;
      this.nextAudioTime = 0;
      this.call = {};
      this.talkgroups = [];
      if (notify) this.state("closed");
    }
  }

  window.OpenR4d10HoseLine = HoseLineReceiver;
})();
