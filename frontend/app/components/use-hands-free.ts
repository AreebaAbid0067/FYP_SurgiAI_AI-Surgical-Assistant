"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type VoiceState = "off" | "waiting" | "recording" | "thinking" | "speaking" | "error";

type Result = { 0: { transcript: string } };
type RecognitionEvent = { results: ArrayLike<Result> };
type Recognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  abort: () => void;
  onresult: ((event: RecognitionEvent) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
};

// Spoken commands. Matching is forgiving because speech recognition is imperfect.
const WAKE = /\bi\s+(have|had|got)\s+(a\s+)?(question|query)\b/i;
const DONE = /\b(please\s+answer|answer\s+please|please\s+reply)\b/i;
const CANCEL = /\b(cancel\s+(that|question)|never\s*mind)\b/i;

export const COMMANDS = { wake: "I have a question", done: "Please answer", cancel: "Cancel that" };

const plainText = (markdown: string) =>
  markdown
    .replace(/[#*_`>|]/g, " ")
    .replace(/\s-\s/g, ", ")
    .replace(/\s+/g, " ")
    .trim();

function chunks(text: string, size = 220): string[] {
  const sentences = text.match(/[^.!?\n]+[.!?]*/g) ?? [text];
  const out: string[] = [];
  let current = "";
  for (const sentence of sentences) {
    if ((current + sentence).length > size && current) {
      out.push(current.trim());
      current = "";
    }
    current += sentence + " ";
  }
  if (current.trim()) out.push(current.trim());
  return out;
}

type Options = {
  lang: string;
  rate: number;
  autoRead: boolean;
  onQuestion: (question: string) => Promise<string | null>;
};

// Hands-free loop: wait for the wake phrase -> record -> "please answer" -> fetch -> read aloud -> wait again.
export function useHandsFree({ lang, rate, autoRead, onQuestion }: Options) {
  const [state, setState] = useState<VoiceState>("off");
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState("");
  const [supported, setSupported] = useState(true);

  const stateRef = useRef<VoiceState>("off");
  const enabled = useRef(false);
  const recognition = useRef<Recognition | null>(null);
  const audio = useRef<AudioContext | null>(null);
  const wakeLock = useRef<{ release: () => Promise<void> } | null>(null);
  const anchor = useRef({ index: 0, offset: 0 });
  const carry = useRef("");
  const latest = useRef({ lang, rate, autoRead, onQuestion });
  latest.current = { lang, rate, autoRead, onQuestion };

  useEffect(() => {
    setSupported("SpeechRecognition" in window || "webkitSpeechRecognition" in window);
  }, []);

  const mode = (next: VoiceState) => {
    stateRef.current = next;
    setState(next);
  };

  const beep = (frequency: number, ms = 160) => {
    const context = audio.current;
    if (!context) return;
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.frequency.value = frequency;
    gain.gain.value = 0.15;
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + ms / 1000);
  };

  const speak = useCallback(
    (text: string) =>
      new Promise<void>((resolve) => {
        const parts = chunks(plainText(text));
        if (!parts.length) return resolve();
        window.speechSynthesis.cancel();
        let remaining = parts.length;
        const finished = () => {
          remaining -= 1;
          if (remaining <= 0) resolve();
        };
        for (const part of parts) {
          const utterance = new SpeechSynthesisUtterance(part);
          utterance.lang = latest.current.lang;
          utterance.rate = latest.current.rate;
          utterance.onend = finished;
          utterance.onerror = finished;
          window.speechSynthesis.speak(utterance);
        }
      }),
    []
  );

  const stopRecognition = () => {
    const current = recognition.current;
    recognition.current = null;
    if (current) {
      current.onend = null;
      current.onresult = null;
      current.onerror = null;
      try { current.abort(); } catch { /* already stopped */ }
    }
  };

  const questionSoFar = (results: ArrayLike<Result>) => {
    let text = "";
    for (let i = anchor.current.index; i < results.length; i++) {
      const piece = results[i][0].transcript;
      text += (i === anchor.current.index ? piece.slice(anchor.current.offset) : piece) + " ";
    }
    return `${carry.current} ${text}`.trim();
  };

  const submit = async (question: string) => {
    stopRecognition();
    mode("thinking");
    beep(520, 220);
    let answer: string | null = null;
    try {
      answer = await latest.current.onQuestion(question);
    } catch {
      answer = "Sorry, I could not get an answer. Please try again.";
    }
    if (!enabled.current) return;
    if (answer && latest.current.autoRead) {
      mode("speaking");
      await speak(answer);
    }
    if (enabled.current) listen();
  };

  const onResult = (event: RecognitionEvent) => {
    const { results } = event;
    if (stateRef.current === "waiting") {
      for (let i = 0; i < results.length; i++) {
        const text = results[i][0].transcript;
        const match = WAKE.exec(text);
        if (match) {
          anchor.current = { index: i, offset: match.index + match[0].length };
          carry.current = "";
          mode("recording");
          beep(880, 150);
          break;
        }
      }
      if ((stateRef.current as VoiceState) !== "recording") return;
    }
    if ((stateRef.current as VoiceState) !== "recording") return;

    const text = questionSoFar(results);
    if (CANCEL.test(text)) {
      stopRecognition();
      beep(300, 250);
      setTranscript("");
      listen();
      return;
    }
    const done = DONE.exec(text);
    if (done) {
      const question = text.slice(0, done.index).replace(/[.,]\s*$/, "").trim();
      if (question) {
        setTranscript(question);
        void submit(question);
      }
      return;
    }
    setTranscript(text);
  };

  const listen = () => {
    stopRecognition();
    const Ctor = (window as unknown as Record<string, new () => Recognition>).SpeechRecognition
      ?? (window as unknown as Record<string, new () => Recognition>).webkitSpeechRecognition;
    const wasRecording = stateRef.current === "recording";
    if (!wasRecording) {
      carry.current = "";
      setTranscript("");
      mode("waiting");
    }
    anchor.current = wasRecording ? { index: 0, offset: 0 } : { index: 0, offset: 0 };
    const rec = new Ctor();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = latest.current.lang;
    rec.onresult = onResult;
    rec.onerror = (event) => {
      if (["not-allowed", "service-not-allowed"].includes(event.error)) {
        enabled.current = false;
        stopRecognition();
        setError("Microphone is blocked. Click the lock icon in the address bar, allow the microphone, then turn hands-free on again.");
        mode("error");
      } else if (event.error === "network") {
        enabled.current = false;
        stopRecognition();
        setError("Voice recognition needs an internet connection. Check the connection and turn hands-free on again.");
        mode("error");
      }
    };
    rec.onend = () => {
      // Browsers end recognition after a pause; carry the question over and resume.
      if (!enabled.current || !["waiting", "recording"].includes(stateRef.current)) return;
      if (stateRef.current === "recording") carry.current = transcriptRef.current;
      setTimeout(() => enabled.current && stateRef.current !== "thinking" && listen(), 150);
    };
    recognition.current = rec;
    try { rec.start(); } catch { /* already starting */ }
  };

  const transcriptRef = useRef("");
  useEffect(() => { transcriptRef.current = transcript; }, [transcript]);

  const start = async () => {
    setError("");
    enabled.current = true;
    audio.current = audio.current ?? new AudioContext();
    try {
      const nav = navigator as unknown as { wakeLock?: { request: (t: string) => Promise<{ release: () => Promise<void> }> } };
      wakeLock.current = (await nav.wakeLock?.request("screen")) ?? null;
    } catch { /* screen lock prevention is best effort */ }
    mode("speaking");
    await speak(`Hands-free is on. Say "${COMMANDS.wake}" when you need me.`);
    if (enabled.current) listen();
  };

  const stop = useCallback(() => {
    enabled.current = false;
    stopRecognition();
    window.speechSynthesis.cancel();
    void wakeLock.current?.release().catch(() => undefined);
    wakeLock.current = null;
    setTranscript("");
    mode("off");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const skipReading = () => window.speechSynthesis.cancel();

  useEffect(() => stop, [stop]);

  return { state, transcript, error, supported, start, stop, skipReading, speak };
}
