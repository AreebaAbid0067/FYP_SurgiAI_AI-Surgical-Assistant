"use client";

import { useRef, useState } from "react";
import { duringSurgery } from "../actions/during-surgery";

type RecognitionLike = {
  lang: string;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

export default function DuringSurgeryWorkspace() {
  const [history, setHistory] = useState("");
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [speak, setSpeak] = useState(true);
  const recognition = useRef<RecognitionLike | null>(null);

  const ask = async (text: string) => {
    const question = text.trim();
    if (!question) return;
    if (!history.trim()) {
      setError("Please enter patient history first.");
      return;
    }
    setLoading(true);
    setError("");
    setAnswer("");
    try {
      const response = await duringSurgery(question, history);
      if (response.status !== 200) {
        setError(response.message ?? "The assistant could not answer.");
        return;
      }
      const text =
        typeof response.data === "string"
          ? response.data
          : JSON.stringify(response.data, null, 2);
      setAnswer(text);
      if (speak && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  };

  const toggleMic = () => {
    if (listening) {
      recognition.current?.stop();
      return;
    }
    const Ctor = (window as unknown as {
      SpeechRecognition?: new () => RecognitionLike;
      webkitSpeechRecognition?: new () => RecognitionLike;
    });
    const Recognition = Ctor.SpeechRecognition ?? Ctor.webkitSpeechRecognition;
    if (!Recognition) {
      setError("Voice input is not supported in this browser. Use Chrome or Edge, or type your question.");
      return;
    }
    const rec = new Recognition();
    rec.lang = "en-US";
    rec.interimResults = false;
    rec.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setQuery(transcript);
      void ask(transcript);
    };
    rec.onerror = () => setError("Voice recognition failed. Check microphone permission.");
    rec.onend = () => setListening(false);
    recognition.current = rec;
    setListening(true);
    rec.start();
  };

  const field =
    "w-full border border-[var(--line)] bg-white p-3 text-sm outline-none focus:border-[var(--green)]";

  return (
    <section className="mt-8 space-y-5">
      <label className="block">
        <span className="eyebrow">Patient history</span>
        <textarea
          className={`${field} mt-2 h-32`}
          value={history}
          onChange={(e) => setHistory(e.target.value)}
          placeholder="Age, conditions, allergies, medications, procedure…"
        />
      </label>

      <label className="block">
        <span className="eyebrow">Surgeon query</span>
        <textarea
          className={`${field} mt-2 h-24`}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. What landmarks confirm the critical view of safety?"
        />
      </label>

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={() => ask(query)}
          disabled={loading || !query.trim()}
          className="bg-[var(--green-dark)] px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          {loading ? "Thinking…" : "Ask AI"}
        </button>
        <button
          onClick={toggleMic}
          disabled={loading}
          className="border border-[var(--green)] px-5 py-2.5 text-sm font-semibold text-[var(--green-dark)] disabled:opacity-50"
        >
          {listening ? "Stop listening" : "Speak"}
        </button>
        <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
          <input type="checkbox" checked={speak} onChange={(e) => setSpeak(e.target.checked)} />
          Read answer aloud
        </label>
      </div>

      {error && (
        <p role="alert" className="border-l-2 border-red-600 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}
      {answer && (
        <div className="border-l-2 border-[var(--green)] bg-white p-4">
          <span className="eyebrow">Response</span>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6">{answer}</p>
        </div>
      )}
    </section>
  );
}
