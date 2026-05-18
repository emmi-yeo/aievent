"use client";
import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ArrowLeft, Copy, CheckCircle2 } from "lucide-react";

interface EngagementCreated {
  id: string;
  client_email: string;
  temp_password?: string;
  email_sent?: boolean;
}

export default function NewEngagementPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    client_name: "",
    client_email: "",
    company: "",
    industry: "",
    deadline: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<EngagementCreated | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const eng = await api.post<EngagementCreated>("/engagements", form);
      if (eng.temp_password) {
        // Always show credentials panel so consultant can copy and share them
        setCreated(eng);
      } else {
        router.push(`/dashboard/${eng.id}`);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create engagement");
    } finally {
      setLoading(false);
    }
  }

  function copyPassword() {
    if (created?.temp_password) {
      navigator.clipboard.writeText(created.temp_password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  const INDUSTRIES = [
    "Technology", "Financial Services", "Healthcare", "Retail & E-commerce",
    "Manufacturing", "Real Estate", "Education", "Hospitality & Tourism",
    "Professional Services", "Energy & Utilities", "Other",
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-navy-900 text-white px-6 py-4 flex items-center gap-3">
        <button onClick={() => router.back()} className="hover:text-gray-300 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-lg font-semibold">New Client Engagement</h1>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-10">
        {/* Credentials modal when email delivery failed */}
        {created && (
          <div className="card border-green-300 bg-green-50 mb-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center shrink-0 text-green-600 font-bold text-lg">
                ✓
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-green-900 mb-1">
                  Engagement created!
                  {created.email_sent ? " — Welcome email sent." : " — Share credentials with your client."}
                </h3>
                <p className="text-green-700 text-sm mb-3">
                  {created.email_sent
                    ? "The client has been emailed their login credentials. Copy them below as a backup."
                    : "Share these login details directly with your client (WhatsApp, email, etc.):"}
                </p>
                <div className="bg-white rounded-lg border border-amber-200 p-3 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Portal URL</span>
                    <span className="font-mono text-gray-800">
                      {typeof window !== "undefined" ? window.location.origin : ""}/login
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Email</span>
                    <span className="font-mono text-gray-800">{created.client_email}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-500">Password</span>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-gray-800 bg-gray-50 px-2 py-0.5 rounded">
                        {created.temp_password}
                      </span>
                      <button
                        onClick={copyPassword}
                        className="text-navy-900 hover:text-accent transition-colors"
                      >
                        {copied
                          ? <CheckCircle2 className="w-4 h-4 text-green-600" />
                          : <Copy className="w-4 h-4" />
                        }
                      </button>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => router.push(`/dashboard/${created.id}`)}
                  className="btn-primary mt-4 text-sm py-2"
                >
                  Continue to Engagement
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="card">
          <h2 className="text-xl font-bold text-navy-900 mb-1">Create Engagement</h2>
          <p className="text-gray-500 text-sm mb-6">
            The client will receive an email with login credentials and instructions to upload their documents.
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Client Name</label>
                <input
                  className="input"
                  value={form.client_name}
                  onChange={(e) => setForm({ ...form, client_name: e.target.value })}
                  required
                  placeholder="John Doe"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Client Email</label>
                <input
                  type="email"
                  className="input"
                  value={form.client_email}
                  onChange={(e) => setForm({ ...form, client_email: e.target.value })}
                  required
                  placeholder="client@company.com"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Company Name</label>
              <input
                className="input"
                value={form.company}
                onChange={(e) => setForm({ ...form, company: e.target.value })}
                required
                placeholder="Acme Corp"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Industry</label>
                <select
                  className="input"
                  value={form.industry}
                  onChange={(e) => setForm({ ...form, industry: e.target.value })}
                  required
                >
                  <option value="">Select industry</option>
                  {INDUSTRIES.map((ind) => (
                    <option key={ind} value={ind}>{ind}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Document Deadline</label>
                <input
                  type="date"
                  className="input"
                  value={form.deadline}
                  onChange={(e) => setForm({ ...form, deadline: e.target.value })}
                  required
                  min={new Date().toISOString().split("T")[0]}
                />
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
                {error}
              </div>
            )}

            <div className="flex gap-3 pt-2">
              <button type="submit" disabled={loading} className="btn-primary flex-1">
                {loading ? "Creating..." : "Create Engagement & Send Invite"}
              </button>
              <button type="button" onClick={() => router.back()} className="btn-secondary">
                Cancel
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
