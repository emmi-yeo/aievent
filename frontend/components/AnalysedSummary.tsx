"use client";
import { useState } from "react";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";

interface Section {
  key: string;
  title: string;
  content: string;
  sources?: string[];
}

interface BriefData {
  executive_summary: string;
  sections: Section[];
  strategic_recommendations: string;
}

function SectionCard({ section }: { section: Section }) {
  const [open, setOpen] = useState(true);

  function renderContent(content: string) {
    return content.split("\n").filter(Boolean).map((line, i) => {
      if (line.match(/^\*\*(.*)\*\*/) || line.match(/^#+\s/)) {
        const clean = line.replace(/^#+\s/, "").replace(/\*\*/g, "");
        return <p key={i} className="font-semibold text-navy-900 mt-3 mb-1">{clean}</p>;
      }
      if (line.match(/^\d+\.\s/)) {
        return <p key={i} className="ml-4 mb-2 text-gray-700">{line}</p>;
      }
      return <p key={i} className="text-gray-700 mb-2 leading-relaxed">{line}</p>;
    });
  }

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-6 py-4 bg-white hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-accent" />
          <h3 className="font-semibold text-navy-900 text-left">{section.title}</h3>
          {section.sources && section.sources.length > 0 && (
            <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full flex items-center gap-1">
              <FileText className="w-3 h-3" />
              {section.sources[0]}
            </span>
          )}
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </button>
      {open && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
          {renderContent(section.content)}
        </div>
      )}
    </div>
  );
}

export default function AnalysedSummary({ brief, company }: { brief: BriefData; company: string }) {
  return (
    <div className="space-y-6">
      {/* Executive Summary */}
      <div className="bg-navy-900 text-white rounded-xl p-6">
        <h2 className="text-lg font-bold mb-3 text-sky">Executive Summary</h2>
        <div className="space-y-2">
          {brief.executive_summary.split("\n").filter(Boolean).map((line, i) => (
            <p key={i} className="text-gray-200 leading-relaxed text-sm">{line}</p>
          ))}
        </div>
      </div>

      {/* Document Sections */}
      <div className="space-y-3">
        <h2 className="text-lg font-bold text-navy-900">Detailed Analysis</h2>
        {brief.sections.map((section) => (
          <SectionCard key={section.key} section={section} />
        ))}
      </div>

      {/* Strategic Recommendations */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
        <h2 className="text-lg font-bold text-navy-900 mb-4">Strategic Recommendations</h2>
        <div className="space-y-2">
          {brief.strategic_recommendations.split("\n").filter(Boolean).map((line, i) => {
            if (line.match(/^\d+\./)) {
              return (
                <div key={i} className="flex gap-3">
                  <span className="text-accent font-bold mt-0.5 shrink-0">
                    {line.match(/^\d+/)![0]}.
                  </span>
                  <p className="text-gray-700 leading-relaxed">
                    {line.replace(/^\d+\.\s*/, "")}
                  </p>
                </div>
              );
            }
            return <p key={i} className="text-gray-700 leading-relaxed">{line}</p>;
          })}
        </div>
      </div>
    </div>
  );
}
