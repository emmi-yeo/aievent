"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { getAuth, clearAuth } from "@/lib/auth";
import { PlusCircle, LogOut, Building2, Calendar, CheckCircle2, Clock, BarChart3 } from "lucide-react";

interface EngagementListItem {
  id: string;
  company: string;
  client_name: string;
  industry: string;
  deadline: string;
  onboarding_complete: boolean;
  status: string;
  upload_summary: Record<string, boolean>;
}

const CATEGORY_LABELS: Record<string, string> = {
  financial_report: "Financial",
  business_plan: "Business Plan",
  market_view: "Market View",
  fact_finding: "Fact Finding",
  value_proposition: "Value Prop",
  pricing_structure: "Pricing",
  market_research: "Market Research",
};

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending: "badge-pending",
    analysing: "badge-analysing",
    complete: "badge-complete",
  };
  return <span className={map[status] || "badge-pending"}>{status}</span>;
}

function UploadProgress({ summary }: { summary: Record<string, boolean> }) {
  const total = Object.keys(summary).length;
  const done = Object.values(summary).filter(Boolean).length;
  const pct = total ? Math.round((done / total) * 100) : 0;
  return (
    <div className="mt-3">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{done}/{total} documents</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-navy-900 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex flex-wrap gap-1 mt-2">
        {Object.entries(summary).map(([cat, uploaded]) => (
          <span
            key={cat}
            className={`text-xs px-2 py-0.5 rounded-full ${
              uploaded ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-400"
            }`}
          >
            {CATEGORY_LABELS[cat] || cat}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [engagements, setEngagements] = useState<EngagementListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const auth = getAuth();
    if (!auth || auth.role !== "consultant") {
      router.replace("/login");
      return;
    }
    fetchEngagements();
  }, [router]);

  async function fetchEngagements() {
    try {
      const data = await api.get<EngagementListItem[]>("/engagements");
      setEngagements(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load engagements");
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    clearAuth();
    router.push("/login");
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-navy-900 text-white px-6 py-4 flex items-center justify-between shadow-lg">
        <div className="flex items-center gap-3">
          <BarChart3 className="w-6 h-6 text-accent" />
          <h1 className="text-lg font-semibold">Market Research Tool</h1>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/dashboard/new")}
            className="flex items-center gap-2 bg-accent hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <PlusCircle className="w-4 h-4" />
            New Engagement
          </button>
          <button
            onClick={logout}
            className="flex items-center gap-2 text-gray-300 hover:text-white text-sm"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-navy-900">Client Engagements</h2>
          <p className="text-gray-500 text-sm mt-1">
            Track document collection and run AI analysis for each client.
          </p>
        </div>

        {loading && (
          <div className="text-center py-16 text-gray-400">Loading engagements...</div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3">
            {error}
          </div>
        )}

        {!loading && engagements.length === 0 && (
          <div className="text-center py-16">
            <Building2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 font-medium">No engagements yet</p>
            <p className="text-gray-400 text-sm mt-1">Create your first client engagement to get started.</p>
            <button
              onClick={() => router.push("/dashboard/new")}
              className="btn-primary mt-4"
            >
              Create Engagement
            </button>
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {engagements.map((eng) => (
            <div
              key={eng.id}
              onClick={() => router.push(`/dashboard/${eng.id}`)}
              className="card cursor-pointer hover:shadow-md hover:border-navy-900 transition-all group"
            >
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-semibold text-navy-900 group-hover:text-accent transition-colors">
                    {eng.company}
                  </h3>
                  <p className="text-sm text-gray-500">{eng.client_name}</p>
                </div>
                <StatusBadge status={eng.status} />
              </div>

              <div className="flex items-center gap-4 text-xs text-gray-400 mt-2">
                <span className="flex items-center gap-1">
                  <Building2 className="w-3.5 h-3.5" /> {eng.industry}
                </span>
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" /> {eng.deadline}
                </span>
              </div>

              <div className="flex items-center gap-1.5 mt-3 text-xs">
                {eng.onboarding_complete ? (
                  <span className="flex items-center gap-1 text-green-600">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Onboarding done
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-yellow-600">
                    <Clock className="w-3.5 h-3.5" /> Onboarding pending
                  </span>
                )}
              </div>

              <UploadProgress summary={eng.upload_summary} />
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
