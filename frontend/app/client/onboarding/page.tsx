"use client";
import { useEffect, useState, useRef, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { getAuth, clearAuth } from "@/lib/auth";
import { Send, Bot, User, ArrowRight, LogOut } from "lucide-react";

interface Message {
  role: "bot" | "user";
  text: string;
}

export default function OnboardingPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [complete, setComplete] = useState(false);
  const [engagementId, setEngagementId] = useState<string | null>(null);
  const [initialising, setInitialising] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const auth = getAuth();
    if (!auth || auth.role !== "client" || !auth.engagement_id) {
      router.replace("/login");
      return;
    }
    setEngagementId(auth.engagement_id);
    initChat(auth.engagement_id);
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function initChat(eid: string) {
    try {
      const res = await api.get<{ reply: string; is_complete: boolean }>(
        `/onboarding/${eid}/start`
      );
      setMessages([{ role: "bot", text: res.reply }]);
      if (res.is_complete) setComplete(true);
    } catch {
      setMessages([{ role: "bot", text: "Welcome! Let's get started with a few questions about your business. What is your company name and what does your business do?" }]);
    } finally {
      setInitialising(false);
    }
  }

  async function sendMessage(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading || !engagementId) return;

    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: userMsg }]);
    setLoading(true);

    try {
      const res = await api.post<{ reply: string; is_complete: boolean }>(
        `/onboarding/${engagementId}/chat`,
        { message: userMsg }
      );
      setMessages((prev) => [...prev, { role: "bot", text: res.reply }]);
      if (res.is_complete) {
        setComplete(true);
      }
    } catch (err: unknown) {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    clearAuth();
    router.push("/login");
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-navy-900 text-white px-6 py-4 flex items-center justify-between shadow-lg">
        <div className="flex items-center gap-3">
          <Bot className="w-5 h-5 text-sky" />
          <div>
            <h1 className="text-base font-semibold">Business Onboarding</h1>
            <p className="text-xs text-gray-400">Step 1 of 2 — Answer a few questions</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {complete && (
            <button
              onClick={() => router.push("/client/upload")}
              className="flex items-center gap-2 bg-accent hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              Upload Documents <ArrowRight className="w-4 h-4" />
            </button>
          )}
          <button onClick={logout} className="text-gray-400 hover:text-white">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Progress steps */}
      <div className="bg-white border-b border-gray-100 px-6 py-3">
        <div className="max-w-2xl mx-auto flex items-center gap-3 text-sm">
          <div className="flex items-center gap-2 text-navy-900 font-medium">
            <div className="w-6 h-6 rounded-full bg-navy-900 text-white flex items-center justify-center text-xs">1</div>
            Business Onboarding
          </div>
          <div className="h-px flex-1 bg-gray-200" />
          <div className={`flex items-center gap-2 ${complete ? "text-gray-500" : "text-gray-300"}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${complete ? "bg-gray-200 text-gray-600" : "border-2 border-gray-200 text-gray-300"}`}>2</div>
            Document Upload
          </div>
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-2xl mx-auto space-y-4">
          {initialising && (
            <div className="text-center text-gray-400 py-8">
              <Bot className="w-8 h-8 mx-auto mb-2 animate-pulse" />
              <p className="text-sm">Starting your onboarding session...</p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                msg.role === "bot" ? "bg-navy-900" : "bg-gray-200"
              }`}>
                {msg.role === "bot"
                  ? <Bot className="w-4 h-4 text-white" />
                  : <User className="w-4 h-4 text-gray-500" />
                }
              </div>
              <div
                className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                  msg.role === "bot"
                    ? "bg-white border border-gray-200 text-gray-800 rounded-tl-sm"
                    : "bg-navy-900 text-white rounded-tr-sm"
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-navy-900 flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}

          {complete && !loading && (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
              <p className="text-green-700 font-medium text-sm">Onboarding complete!</p>
              <p className="text-green-600 text-xs mt-1">
                Now upload your business documents to continue.
              </p>
              <button
                onClick={() => router.push("/client/upload")}
                className="mt-3 btn-primary text-sm py-2"
              >
                Proceed to Document Upload
              </button>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      {!complete && (
        <div className="bg-white border-t border-gray-200 px-4 py-4">
          <form onSubmit={sendMessage} className="max-w-2xl mx-auto flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading || initialising}
              className="input flex-1"
              placeholder="Type your answer..."
            />
            <button
              type="submit"
              disabled={loading || !input.trim() || initialising}
              className="bg-navy-900 hover:bg-navy-800 disabled:opacity-50 text-white p-2.5 rounded-lg transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
