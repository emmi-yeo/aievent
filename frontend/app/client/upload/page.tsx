"use client";
import { useEffect, useState, useRef, ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { getAuth, clearAuth } from "@/lib/auth";
import {
  CheckCircle2, Upload, FileText, X, ArrowLeft, LogOut, AlertCircle,
} from "lucide-react";

const CATEGORIES = [
  { key: "financial_report",   label: "Financial Report",   hint: "Annual report, P&L, balance sheet, cash flow statement" },
  { key: "business_plan",      label: "Business Plan",      hint: "Strategic plan, growth roadmap, company overview" },
  { key: "market_view",        label: "Market View",        hint: "How you see your market, your positioning document" },
  { key: "fact_finding",       label: "Fact Finding",       hint: "Research notes, data gathered, discovery documents" },
  { key: "value_proposition",  label: "Value Proposition",  hint: "Your value prop document, pitch deck, USP statement" },
  { key: "pricing_structure",  label: "Pricing Structure",  hint: "Pricing model, tier breakdown, revenue structure" },
  { key: "market_research",    label: "Market Research",    hint: "Industry reports, competitor analysis, market data" },
];

type FileStatus = { id: string; filename: string; status: string };
type CategoryData = { label: string; uploaded: boolean; files: FileStatus[] };

export default function UploadPage() {
  const router = useRouter();
  const [engagementId, setEngagementId] = useState<string | null>(null);
  const [checklist, setChecklist] = useState<Record<string, CategoryData>>({});
  const [uploading, setUploading] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  useEffect(() => {
    const auth = getAuth();
    if (!auth || auth.role !== "client" || !auth.engagement_id) {
      router.replace("/login");
      return;
    }
    setEngagementId(auth.engagement_id);
    loadChecklist(auth.engagement_id);
  }, [router]);

  async function loadChecklist(eid: string) {
    try {
      const data = await api.get<{ categories: Record<string, CategoryData> }>(
        `/uploads/${eid}`
      );
      setChecklist(data.categories);
    } catch {}
    setLoading(false);
  }

  async function handleFileChange(category: string, e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !engagementId) return;

    setUploading(category);
    setErrors((prev) => ({ ...prev, [category]: "" }));

    const form = new FormData();
    form.append("category", category);
    form.append("file", file);

    try {
      await api.postForm(`/uploads/${engagementId}`, form);
      await loadChecklist(engagementId);
    } catch (err: unknown) {
      setErrors((prev) => ({
        ...prev,
        [category]: err instanceof Error ? err.message : "Upload failed",
      }));
    } finally {
      setUploading(null);
      if (inputRefs.current[category]) {
        inputRefs.current[category]!.value = "";
      }
    }
  }

  function handleDrop(category: string, e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (!file || !engagementId) return;
    const fakeEvent = { target: { files: [file] } } as unknown as ChangeEvent<HTMLInputElement>;
    handleFileChange(category, fakeEvent);
  }

  const uploadedCount = Object.values(checklist).filter((c) => c.uploaded).length;
  const totalCount = CATEGORIES.length;
  const allDone = uploadedCount === totalCount;

  function logout() {
    clearAuth();
    router.push("/login");
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-navy-900 text-white px-6 py-4 flex items-center justify-between shadow-lg">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/client/onboarding")} className="hover:text-gray-300">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-base font-semibold">Document Upload</h1>
            <p className="text-xs text-gray-400">Step 2 of 2 — Upload your business documents</p>
          </div>
        </div>
        <button onClick={logout} className="text-gray-400 hover:text-white">
          <LogOut className="w-4 h-4" />
        </button>
      </header>

      {/* Progress bar */}
      <div className="bg-white border-b border-gray-100 px-6 py-3">
        <div className="max-w-3xl mx-auto">
          <div className="flex justify-between text-sm text-gray-600 mb-1.5">
            <span className="font-medium">{uploadedCount} of {totalCount} documents uploaded</span>
            {allDone && <span className="text-green-600 font-medium flex items-center gap-1"><CheckCircle2 className="w-4 h-4" /> All done!</span>}
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-navy-900 rounded-full transition-all duration-500"
              style={{ width: `${(uploadedCount / totalCount) * 100}%` }}
            />
          </div>
        </div>
      </div>

      <main className="max-w-3xl mx-auto px-6 py-8">
        {allDone && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6 flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-green-600 shrink-0" />
            <div>
              <p className="text-green-800 font-medium text-sm">All documents uploaded successfully!</p>
              <p className="text-green-600 text-xs mt-0.5">Your consultant will be notified and can now run the analysis.</p>
            </div>
          </div>
        )}

        {loading ? (
          <div className="text-center py-16 text-gray-400">Loading...</div>
        ) : (
          <div className="space-y-4">
            {CATEGORIES.map(({ key, label, hint }) => {
              const catData = checklist[key];
              const isUploaded = catData?.uploaded;
              const isUploading = uploading === key;
              const catError = errors[key];
              const files = catData?.files || [];

              return (
                <div
                  key={key}
                  className={`card transition-all ${isUploaded ? "border-green-200 bg-green-50/30" : "hover:border-navy-900"}`}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => handleDrop(key, e)}
                >
                  <div className="flex items-start gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                      isUploaded ? "bg-green-100" : "bg-gray-100"
                    }`}>
                      {isUploaded
                        ? <CheckCircle2 className="w-5 h-5 text-green-600" />
                        : <Upload className="w-5 h-5 text-gray-400" />
                      }
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h3 className="font-semibold text-navy-900">{label}</h3>
                        {isUploaded && (
                          <span className="text-xs text-green-600 font-medium">Uploaded</span>
                        )}
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5">{hint}</p>

                      {/* Uploaded files list */}
                      {files.length > 0 && (
                        <div className="mt-2 space-y-1">
                          {files.map((f) => (
                            <div key={f.id} className="flex items-center gap-2 text-xs text-gray-500">
                              <FileText className="w-3 h-3" />
                              <span className="truncate">{f.filename}</span>
                              <span className={`px-1.5 py-0.5 rounded text-xs ${
                                f.status === "ready" ? "bg-green-100 text-green-700"
                                : f.status === "error" ? "bg-red-100 text-red-700"
                                : "bg-yellow-100 text-yellow-700"
                              }`}>{f.status}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {catError && (
                        <div className="mt-2 flex items-center gap-1.5 text-xs text-red-600">
                          <AlertCircle className="w-3.5 h-3.5" /> {catError}
                        </div>
                      )}
                    </div>

                    <div className="shrink-0">
                      <input
                        type="file"
                        ref={(el) => { inputRefs.current[key] = el; }}
                        onChange={(e) => handleFileChange(key, e)}
                        className="hidden"
                        accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.png,.jpg,.jpeg"
                        id={`file-${key}`}
                      />
                      <label
                        htmlFor={`file-${key}`}
                        className={`cursor-pointer inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                          isUploading
                            ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                            : isUploaded
                            ? "bg-green-100 text-green-700 hover:bg-green-200"
                            : "bg-navy-900 text-white hover:bg-navy-800"
                        }`}
                      >
                        {isUploading ? (
                          <span className="flex items-center gap-1.5">
                            <div className="w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                            Uploading...
                          </span>
                        ) : isUploaded ? (
                          "Replace"
                        ) : (
                          <><Upload className="w-3.5 h-3.5" /> Upload</>
                        )}
                      </label>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <p className="text-xs text-gray-400 text-center mt-6">
          Accepted formats: PDF, Word, Excel, CSV, TXT, PNG, JPG
        </p>
      </main>
    </div>
  );
}
