"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { api, streamAnalysis, API_URL } from "@/lib/api";
import { getAuth } from "@/lib/auth";
import AnalysedSummary from "@/components/AnalysedSummary";
import {
  ArrowLeft, Play, Download, CheckCircle2, Clock, RefreshCw,
  Building2, Calendar, FileText,
} from "lucide-react";

interface Engagement {
  id: string;
  company: string;
  client_name: string;
  client_email: string;
  industry: string;
  deadline: string;
  onboarding_complete: boolean;
  status: string;
  brief_json?: string;
}

interface ChecklistStatus {
  engagement_id: string;
  categories: Record<string, { label: string; uploaded: boolean; files: { id: string; filename: string; status: string }[] }>;
  all_complete: boolean;
}

interface BriefSection {
  key: string;
  title: string;
  content: string;
  sources: string[];
}

interface Brief {
  executive_summary: string;
  sections: BriefSection[];
  strategic_recommendations: string;
}

export default function EngagementDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;

  const [engagement, setEngagement] = useState<Engagement | null>(null);
  const [checklist, setChecklist] = useState<ChecklistStatus | null>(null);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [streamLog, setStreamLog] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const auth = getAuth();
    if (!auth || auth.role !== "consultant") {
      router.replace("/login");
      return;
    }
    loadData();
  }, [id, router]);

  async function loadData() {
    try {
      const [eng, cl] = await Promise.all([
        api.get<Engagement>(`/engagements/${id}`),
        api.get<ChecklistStatus>(`/uploads/${id}`),
      ]);
      setEngagement(eng);
      setChecklist(cl);
      if (eng.brief_json) {
        setBrief(JSON.parse(eng.brief_json));
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function runAnalysis() {
    setStreaming(true);
    setStreamLog([]);
    const newBrief: Brief = { executive_summary: "", sections: [], strategic_recommendations: "" };

    try {
      await streamAnalysis(id, (data) => {
        if (data.event === "section") {
          const key = data.key as string;
          const title = data.title as string;
          const content = data.content as string;
          setStreamLog((prev) => [...prev, `Generating: ${title}...`]);
          if (key === "executive_summary") {
            newBrief.executive_summary = content;
          } else if (key === "strategic_recommendations") {
            newBrief.strategic_recommendations = content;
          } else {
            const existing = newBrief.sections.find((s) => s.key === key);
            if (!existing) {
              newBrief.sections.push({ key, title, content, sources: [title] });
            }
          }
          setBrief({ ...newBrief });
        } else if (data.event === "done") {
          setStreamLog((prev) => [...prev, "Analysis complete!"]);
          if (data.brief) setBrief(data.brief as Brief);
          loadData();
        } else if (data.event === "error") {
          setError(data.message as string);
        }
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setStreaming(false);
    }
  }

  async function downloadPDF() {
    const token = localStorage.getItem("token");
    const res = await fetch(`${API_URL}/report/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${engagement?.company}_Strategy_Brief.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-400">Loading...</div>;
  }

  if (!engagement) return null;

  const readyUploads = checklist
    ? Object.values(checklist.categories).filter((c) => c.uploaded).length
    : 0;
  const totalCats = checklist ? Object.keys(checklist.categories).length : 7;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-navy-900 text-white px-6 py-4 flex items-center justify-between shadow-lg">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/dashboard")} className="hover:text-gray-300">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-lg font-semibold">{engagement.company}</h1>
            <p className="text-xs text-gray-400">{engagement.client_name} · {engagement.industry}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {brief && (
            <button
              onClick={downloadPDF}
              className="flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              <Download className="w-4 h-4" />
              Download PDF
            </button>
          )}
          <button
            onClick={runAnalysis}
            disabled={streaming || readyUploads === 0}
            className="flex items-center gap-2 bg-accent hover:bg-red-600 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {streaming ? (
              <><RefreshCw className="w-4 h-4 animate-spin" /> Analysing...</>
            ) : (
              <><Play className="w-4 h-4" /> {brief ? "Re-run Analysis" : "Run Analysis"}</>
            )}
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 grid grid-cols-3 gap-6">
        {/* Left: Info + Checklist */}
        <div className="col-span-1 space-y-4">
          <div className="card">
            <h3 className="font-semibold text-navy-900 mb-3">Engagement Details</h3>
            <div className="space-y-2 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4 text-gray-400" />
                <span>{engagement.industry}</span>
              </div>
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-gray-400" />
                <span>Deadline: {engagement.deadline}</span>
              </div>
              <div className="flex items-center gap-2">
                {engagement.onboarding_complete ? (
                  <><CheckCircle2 className="w-4 h-4 text-green-500" /><span className="text-green-700">Onboarding complete</span></>
                ) : (
                  <><Clock className="w-4 h-4 text-yellow-500" /><span className="text-yellow-700">Onboarding pending</span></>
                )}
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-navy-900">Document Checklist</h3>
              <span className="text-xs text-gray-400">{readyUploads}/{totalCats}</span>
            </div>
            <div className="space-y-2">
              {checklist && Object.entries(checklist.categories).map(([key, cat]) => (
                <div key={key} className="flex items-center gap-2">
                  {cat.uploaded ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border-2 border-gray-300 shrink-0" />
                  )}
                  <span className={`text-sm ${cat.uploaded ? "text-gray-700" : "text-gray-400"}`}>
                    {cat.label}
                  </span>
                  {cat.files.length > 0 && (
                    <span className="text-xs text-gray-400 ml-auto flex items-center gap-1">
                      <FileText className="w-3 h-3" />{cat.files.length}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Stream log */}
          {streamLog.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-navy-900 mb-2 text-sm">Analysis Progress</h3>
              <div className="space-y-1">
                {streamLog.map((log, i) => (
                  <p key={i} className="text-xs text-gray-500 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3 h-3 text-green-500 shrink-0" />
                    {log}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Brief */}
        <div className="col-span-2">
          {!brief && !streaming && (
            <div className="text-center py-20 bg-white rounded-xl border border-dashed border-gray-200">
              <Play className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="font-medium text-gray-500">No analysis yet</p>
              <p className="text-sm text-gray-400 mt-1">
                {readyUploads === 0
                  ? "Waiting for client to upload documents"
                  : "Click 'Run Analysis' to generate the strategic brief"}
              </p>
            </div>
          )}

          {brief && <AnalysedSummary brief={brief} company={engagement.company} />}

          {streaming && !brief && (
            <div className="text-center py-20 bg-white rounded-xl border border-gray-200">
              <RefreshCw className="w-10 h-10 text-navy-900 mx-auto mb-4 animate-spin" />
              <p className="font-medium text-gray-600">Gemini is analysing the documents...</p>
              <p className="text-sm text-gray-400 mt-1">This may take 1-2 minutes</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm mt-4">
              {error}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
