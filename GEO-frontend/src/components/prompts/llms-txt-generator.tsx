"use client";

import { useState, useRef, useEffect } from "react";
import {
    Globe, Copy, Download, CheckCircle2, AlertCircle, Loader2,
    FileText, ArrowRight, ExternalLink, ChevronDown, ChevronRight,
    Sparkles, Info, Search, RotateCcw, Eye, Code, X
} from "lucide-react";
import { Button } from "@/components/ui/button";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PageAnalyzed {
    url: string;
    title: string;
    section: string;
    importance: number;
    include: boolean;
}

interface GenerationResult {
    llms_txt: string;
    domain: string;
    stats: {
        total_urls_discovered: number;
        pages_extracted: number;
        pages_included: number;
        sections: Record<string, number>;
    };
    pages_analyzed: PageAnalyzed[];
}

// ─── Tab Buttons ───────────────────────────────────────────────────────────────

function TabButton({
    active,
    onClick,
    icon: Icon,
    label
}: {
    active: boolean;
    onClick: () => void;
    icon: any;
    label: string;
}) {
    return (
        <button
            onClick={onClick}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg transition-all ${active
                ? "bg-teal-50 text-teal-700 border border-teal-200"
                : "text-gray-500 hover:bg-gray-50 hover:text-gray-700 border border-transparent"
                }`}
        >
            <Icon className="h-4 w-4" />
            {label}
        </button>
    );
}

// ─── Main Component ────────────────────────────────────────────────────────────

export function LlmsTxtGenerator() {
    const [url, setUrl] = useState("");
    const [isGenerating, setIsGenerating] = useState(false);
    const [progress, setProgress] = useState(0);
    const [progressStep, setProgressStep] = useState("");
    const [result, setResult] = useState<GenerationResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);
    const [activeTab, setActiveTab] = useState<"preview" | "raw" | "pages">("preview");
    const [sectionsExpanded, setSectionsExpanded] = useState<Record<string, boolean>>({});
    const pollingRef = useRef<NodeJS.Timeout | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Clean up polling on unmount
    useEffect(() => {
        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
        };
    }, []);

    const handleGenerate = async () => {
        if (!url.trim()) return;

        setIsGenerating(true);
        setProgress(0);
        setProgressStep("Initializing...");
        setResult(null);
        setError(null);
        setCopied(false);

        try {
            const token = localStorage.getItem("token");
            const res = await fetch(`${API_BASE_URL}/api/llms-txt/generate`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ url: url.trim() }),
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || `Request failed (${res.status})`);
            }

            const data = await res.json();
            const taskId = data.task_id;

            // Start polling
            pollingRef.current = setInterval(async () => {
                try {
                    const statusRes = await fetch(
                        `${API_BASE_URL}/api/llms-txt/status/${taskId}`,
                        { headers: { Authorization: `Bearer ${token}` } }
                    );

                    if (!statusRes.ok) return;

                    const statusData = await statusRes.json();
                    setProgress(statusData.progress || 0);
                    setProgressStep(statusData.step || "Processing...");

                    if (statusData.status === "completed") {
                        if (pollingRef.current) clearInterval(pollingRef.current);
                        setResult(statusData.result);
                        setIsGenerating(false);
                    } else if (statusData.status === "error") {
                        if (pollingRef.current) clearInterval(pollingRef.current);
                        setError(statusData.error || "An error occurred during generation.");
                        setIsGenerating(false);
                    }
                } catch {
                    // Continue polling on transient errors
                }
            }, 2000);
        } catch (err: any) {
            setError(err.message || "Failed to start generation.");
            setIsGenerating(false);
        }
    };

    const handleCopy = () => {
        if (!result?.llms_txt) return;
        navigator.clipboard.writeText(result.llms_txt);
        setCopied(true);
        setTimeout(() => setCopied(false), 3000);
    };

    const handleDownload = () => {
        if (!result?.llms_txt) return;
        const blob = new Blob([result.llms_txt], { type: "text/plain" });
        const downloadUrl = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = "llms.txt";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(downloadUrl);
    };

    const handleReset = () => {
        setUrl("");
        setResult(null);
        setError(null);
        setIsGenerating(false);
        setProgress(0);
        setProgressStep("");
        setCopied(false);
        if (pollingRef.current) clearInterval(pollingRef.current);
        inputRef.current?.focus();
    };

    const toggleSection = (section: string) => {
        setSectionsExpanded((prev) => ({ ...prev, [section]: !prev[section] }));
    };

    // ─── Render helpers ──────────────────────────────────────────────────────────

    const renderPreview = () => {
        if (!result?.llms_txt) return null;
        const lines = result.llms_txt.split("\n");

        return (
            <div className="font-mono text-sm leading-relaxed space-y-1 max-h-[500px] overflow-y-auto pr-2">
                {lines.map((line, i) => {
                    let className = "text-gray-600";
                    if (line.startsWith("# ")) className = "text-gray-900 font-bold text-lg mt-2";
                    else if (line.startsWith("## ")) className = "text-teal-700 font-semibold text-base mt-4 mb-1";
                    else if (line.startsWith("> ")) className = "text-gray-700 italic border-l-3 border-teal-400 pl-3 py-1 bg-teal-50/50 rounded-r";
                    else if (line.startsWith("- [")) className = "text-gray-700 ml-2";

                    return (
                        <div key={i} className={className}>
                            {line.startsWith("- [") ? (
                                <span>
                                    <span className="text-gray-400 mr-1">•</span>
                                    {renderLink(line.substring(2))}
                                </span>
                            ) : (
                                line || <br />
                            )}
                        </div>
                    );
                })}
            </div>
        );
    };

    const renderLink = (text: string) => {
        const match = text.match(/\[(.+?)\]\((.+?)\)(?::\s*(.+))?/);
        if (!match) return <span>{text}</span>;
        const [, title, href, desc] = match;

        return (
            <span>
                <a href={href} target="_blank" rel="noopener noreferrer"
                    className="text-teal-600 hover:text-teal-800 underline underline-offset-2 decoration-teal-300 hover:decoration-teal-500 transition-colors">
                    {title}
                </a>
                {desc && <span className="text-gray-500">: {desc}</span>}
            </span>
        );
    };

    const renderPagesTable = () => {
        if (!result?.pages_analyzed) return null;

        // Group by section
        const bySection: Record<string, PageAnalyzed[]> = {};
        result.pages_analyzed.forEach((p) => {
            const section = p.section || "Other";
            if (!bySection[section]) bySection[section] = [];
            bySection[section].push(p);
        });

        const sectionOrder = ["Homepage", "Documentation", "API Reference", "Tutorials", "Integrations", "Changelog", "Blog", "Pricing", "About", "Other"];
        const orderedSections = sectionOrder.filter(s => bySection[s]).concat(Object.keys(bySection).filter(s => !sectionOrder.includes(s)));

        return (
            <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
                {orderedSections.map((section) => {
                    const pages = bySection[section];
                    if (!pages) return null;
                    const isExpanded = sectionsExpanded[section] ?? false;
                    const includedCount = pages.filter(p => p.include).length;

                    return (
                        <div key={section} className="border border-gray-200 rounded-xl overflow-hidden">
                            <button
                                onClick={() => toggleSection(section)}
                                className="w-full flex items-center justify-between px-4 py-3 bg-gray-50/80 hover:bg-gray-100 transition-colors"
                            >
                                <div className="flex items-center gap-3">
                                    {isExpanded ? <ChevronDown className="h-4 w-4 text-gray-400" /> : <ChevronRight className="h-4 w-4 text-gray-400" />}
                                    <span className="font-semibold text-sm text-gray-800">{section}</span>
                                    <span className="text-xs text-gray-500 bg-gray-200 rounded-full px-2 py-0.5">
                                        {includedCount}/{pages.length} included
                                    </span>
                                </div>
                            </button>

                            {isExpanded && (
                                <div className="divide-y divide-gray-100">
                                    {pages
                                        .sort((a, b) => b.importance - a.importance)
                                        .map((page, idx) => (
                                            <div key={idx} className={`flex items-center gap-3 px-4 py-2.5 text-sm ${page.include ? "bg-white" : "bg-gray-50 opacity-60"}`}>
                                                <div className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${page.include
                                                    ? page.importance >= 7 ? "bg-teal-100 text-teal-700"
                                                        : page.importance >= 4 ? "bg-amber-100 text-amber-700"
                                                            : "bg-gray-100 text-gray-500"
                                                    : "bg-red-50 text-red-400"}`}>
                                                    {page.importance}
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="font-medium text-gray-800 truncate">{page.title}</div>
                                                    <div className="text-xs text-gray-400 truncate">{page.url}</div>
                                                </div>
                                                {page.include ? (
                                                    <CheckCircle2 className="h-4 w-4 text-teal-500 flex-shrink-0" />
                                                ) : (
                                                    <X className="h-4 w-4 text-red-400 flex-shrink-0" />
                                                )}
                                            </div>
                                        ))}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        );
    };

    // ─── Main Render ─────────────────────────────────────────────────────────────

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Hero Header */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-teal-600 via-teal-500 to-emerald-500 px-8 py-10">
                <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0djZoLTZWMzRoNnptMC0zMHY2aC02VjRoNnptMCAxMnY2aC02VjE2aDZ6bTAgMTJ2Nmg2djZoNnYtNmgtNnYtNmgtNnptMTIgMTJ2Nmg2di02aC02em0xMi0xMnY2aDZ2LTZoLTZ6Ii8+PC9nPjwvZz48L3N2Zz4=')] opacity-30" />
                <div className="relative">
                    <div className="flex items-center gap-2 mb-3">
                        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/15 backdrop-blur-sm text-white/90 text-xs font-medium">
                            <Sparkles className="h-3.5 w-3.5" />
                            Free Tool
                        </div>
                    </div>
                    <h1 className="text-3xl font-extrabold text-white tracking-tight mb-2">
                        LLMs.txt Generator
                    </h1>
                    <p className="text-white/80 text-sm max-w-xl leading-relaxed">
                        Create an optimized llms.txt file for your website to help AI models like ChatGPT,
                        Gemini, and Claude understand your site&apos;s structure, content, and authority.
                    </p>
                </div>
            </div>

            {/* URL Input Card */}
            <div className="dashboard-card p-6">
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-1.5">
                            Enter Your Website URL
                        </label>
                        <div className="flex gap-3">
                            <div className="relative flex-1">
                                <Globe className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4.5 w-4.5 text-gray-400" />
                                <input
                                    ref={inputRef}
                                    type="url"
                                    value={url}
                                    onChange={(e) => setUrl(e.target.value)}
                                    onKeyDown={(e) => e.key === "Enter" && !isGenerating && handleGenerate()}
                                    placeholder="https://example.com"
                                    disabled={isGenerating}
                                    className="w-full pl-11 pr-4 py-3 rounded-xl border border-gray-200 bg-white text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-all disabled:opacity-50"
                                />
                            </div>
                            {result ? (
                                <Button onClick={handleReset} variant="outline"
                                    className="px-5 py-3 rounded-xl border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-800 h-auto">
                                    <RotateCcw className="h-4 w-4 mr-2" />
                                    New
                                </Button>
                            ) : (
                                <Button
                                    onClick={handleGenerate}
                                    disabled={isGenerating || !url.trim()}
                                    className="px-6 py-3 rounded-xl bg-teal-500 hover:bg-teal-600 text-white font-semibold h-auto shadow-lg shadow-teal-500/20 hover:shadow-teal-500/30 transition-all disabled:opacity-50 disabled:shadow-none"
                                >
                                    {isGenerating ? (
                                        <>
                                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                            Generating...
                                        </>
                                    ) : (
                                        <>
                                            Generate
                                            <ArrowRight className="h-4 w-4 ml-2" />
                                        </>
                                    )}
                                </Button>
                            )}
                        </div>
                        <p className="mt-2 text-xs text-gray-400">
                            Enter the root URL of your website. We&apos;ll crawl your sitemap, extract page content,
                            and use AI to generate an optimized llms.txt file.
                        </p>
                    </div>
                </div>
            </div>

            {/* Progress Bar */}
            {isGenerating && (
                <div className="dashboard-card p-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="h-10 w-10 rounded-xl bg-teal-50 flex items-center justify-center">
                                    <Loader2 className="h-5 w-5 text-teal-600 animate-spin" />
                                </div>
                                <div>
                                    <h3 className="text-sm font-semibold text-gray-900">Generating llms.txt</h3>
                                    <p className="text-xs text-gray-500 mt-0.5">{progressStep}</p>
                                </div>
                            </div>
                            <span className="text-sm font-bold text-teal-600">{progress}%</span>
                        </div>

                        <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
                            <div
                                className="bg-gradient-to-r from-teal-500 to-emerald-400 h-full rounded-full transition-all duration-700 ease-out"
                                style={{ width: `${progress}%` }}
                            />
                        </div>

                        <div className="grid grid-cols-4 gap-3">
                            {[
                                { label: "URL Discovery", range: [0, 25], icon: Search },
                                { label: "Content Extraction", range: [25, 50], icon: FileText },
                                { label: "AI Analysis", range: [50, 75], icon: Sparkles },
                                { label: "Final Generation", range: [75, 100], icon: Code },
                            ].map((phase, i) => {
                                const isActive = progress >= phase.range[0] && progress < phase.range[1];
                                const isDone = progress >= phase.range[1];
                                return (
                                    <div key={i} className={`flex items-center gap-2 p-2.5 rounded-lg border transition-all ${isDone ? "bg-teal-50 border-teal-200" :
                                        isActive ? "bg-white border-teal-300 shadow-sm" :
                                            "bg-gray-50 border-gray-100"
                                        }`}>
                                        {isDone ? (
                                            <CheckCircle2 className="h-4 w-4 text-teal-500 flex-shrink-0" />
                                        ) : isActive ? (
                                            <Loader2 className="h-4 w-4 text-teal-500 animate-spin flex-shrink-0" />
                                        ) : (
                                            <phase.icon className="h-4 w-4 text-gray-300 flex-shrink-0" />
                                        )}
                                        <span className={`text-xs font-medium truncate ${isDone ? "text-teal-700" : isActive ? "text-gray-800" : "text-gray-400"}`}>
                                            {phase.label}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}

            {/* Error */}
            {error && (
                <div className="dashboard-card border-red-200 bg-red-50/50 p-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
                    <div className="flex items-start gap-3">
                        <AlertCircle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
                        <div>
                            <h3 className="font-semibold text-red-800 text-sm">Generation Failed</h3>
                            <p className="text-red-600 text-sm mt-1">{error}</p>
                            <Button variant="outline" onClick={handleReset}
                                className="mt-3 text-xs border-red-200 text-red-700 hover:bg-red-100">
                                Try Again
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* Results */}
            {result && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-6 duration-500">
                    {/* Stats Cards */}
                    <div className="grid grid-cols-4 gap-4">
                        {[
                            { label: "URLs Discovered", value: result.stats.total_urls_discovered, color: "cyan" },
                            { label: "Pages Extracted", value: result.stats.pages_extracted, color: "blue" },
                            { label: "Pages Included", value: result.stats.pages_included, color: "emerald" },
                            { label: "Sections", value: Object.keys(result.stats.sections).length, color: "amber" },
                        ].map((stat, i) => (
                            <div key={i} className={`metric-card metric-card-${stat.color}`}>
                                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{stat.label}</p>
                                <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
                            </div>
                        ))}
                    </div>

                    {/* Sections Breakdown */}
                    {Object.keys(result.stats.sections).length > 0 && (
                        <div className="dashboard-card p-5">
                            <h3 className="text-sm font-semibold text-gray-800 mb-3">Sections Found</h3>
                            <div className="flex flex-wrap gap-2">
                                {Object.entries(result.stats.sections).map(([section, count]) => (
                                    <span key={section}
                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-50 border border-gray-200 text-xs font-medium text-gray-700">
                                        {section}
                                        <span className="bg-teal-100 text-teal-700 rounded-full px-1.5 py-0.5 text-[10px] font-bold">
                                            {count}
                                        </span>
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Output Tabs */}
                    <div className="dashboard-card overflow-hidden">
                        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-3">
                            <div className="flex items-center gap-1">
                                <TabButton active={activeTab === "preview"} onClick={() => setActiveTab("preview")}
                                    icon={Eye} label="Preview" />
                                <TabButton active={activeTab === "raw"} onClick={() => setActiveTab("raw")}
                                    icon={Code} label="Raw" />
                                <TabButton active={activeTab === "pages"} onClick={() => setActiveTab("pages")}
                                    icon={FileText} label="All Pages" />
                            </div>

                            <div className="flex items-center gap-2">
                                <Button variant="outline" onClick={handleCopy} size="sm"
                                    className="text-xs border-gray-200 hover:bg-gray-50 rounded-lg">
                                    {copied ? (
                                        <><CheckCircle2 className="h-3.5 w-3.5 mr-1.5 text-teal-500" /> Copied!</>
                                    ) : (
                                        <><Copy className="h-3.5 w-3.5 mr-1.5" /> Copy</>
                                    )}
                                </Button>
                                <Button variant="outline" onClick={handleDownload} size="sm"
                                    className="text-xs border-gray-200 hover:bg-gray-50 rounded-lg">
                                    <Download className="h-3.5 w-3.5 mr-1.5" />
                                    Download
                                </Button>
                            </div>
                        </div>

                        <div className="p-5">
                            {activeTab === "preview" && renderPreview()}
                            {activeTab === "raw" && (
                                <pre className="text-xs leading-relaxed text-gray-700 bg-gray-50 border border-gray-200 rounded-xl p-4 max-h-[500px] overflow-y-auto font-mono whitespace-pre-wrap">
                                    {result.llms_txt}
                                </pre>
                            )}
                            {activeTab === "pages" && renderPagesTable()}
                        </div>
                    </div>

                    {/* Installation CTA */}
                    <div className="dashboard-card p-6 bg-gradient-to-br from-gray-50 to-white">
                        <div className="flex items-start gap-4">
                            <div className="h-11 w-11 rounded-xl bg-teal-100 flex items-center justify-center flex-shrink-0">
                                <Info className="h-5 w-5 text-teal-600" />
                            </div>
                            <div className="space-y-3">
                                <div>
                                    <h3 className="font-semibold text-gray-900 text-sm">How to Install Your llms.txt</h3>
                                    <p className="text-xs text-gray-500 mt-1">Follow these steps to make your llms.txt file accessible to AI models.</p>
                                </div>

                                <div className="space-y-2.5">
                                    {[
                                        {
                                            step: 1,
                                            title: "Download the file",
                                            desc: "Click the Download button above to save your generated llms.txt file."
                                        },
                                        {
                                            step: 2,
                                            title: "Upload to your root directory",
                                            desc: `Place the file at https://${result.domain}/llms.txt so it's publicly accessible.`
                                        },
                                        {
                                            step: 3,
                                            title: "Verify installation",
                                            desc: `Visit https://${result.domain}/llms.txt in your browser to confirm it's working.`
                                        }
                                    ].map((item) => (
                                        <div key={item.step} className="flex items-start gap-3">
                                            <div className="w-6 h-6 rounded-full bg-teal-500 text-white flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                                                {item.step}
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-gray-800">{item.title}</p>
                                                <p className="text-xs text-gray-500">{item.desc}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Best Practices */}
                    <div className="dashboard-card p-6">
                        <h3 className="font-semibold text-gray-900 text-sm mb-4">Best Practices for llms.txt</h3>
                        <div className="grid grid-cols-2 gap-4">
                            {[
                                {
                                    title: "Keep it updated",
                                    desc: "Regenerate your llms.txt whenever you add significant new pages or restructure your site.",
                                    icon: RotateCcw
                                },
                                {
                                    title: "Use descriptive summaries",
                                    desc: "Each page entry should have a unique, specific description—not generic marketing copy.",
                                    icon: FileText
                                },
                                {
                                    title: "Prioritize key content",
                                    desc: "Put your most important pages first. Documentation and API references rank higher.",
                                    icon: Sparkles
                                },
                                {
                                    title: "Link to llms-full.txt",
                                    desc: "For large sites (150+ pages), create an extended version and reference it from the main file.",
                                    icon: ExternalLink
                                }
                            ].map((item, i) => (
                                <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-gray-50/80 border border-gray-100">
                                    <item.icon className="h-4 w-4 text-teal-500 mt-0.5 flex-shrink-0" />
                                    <div>
                                        <p className="text-sm font-medium text-gray-800">{item.title}</p>
                                        <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{item.desc}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* What is llms.txt? */}
                    <div className="dashboard-card p-6">
                        <h3 className="font-semibold text-gray-900 text-sm mb-3">What is llms.txt?</h3>
                        <p className="text-sm text-gray-600 leading-relaxed">
                            The <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">llms.txt</code> standard
                            (defined at <a href="https://llmstxt.org" target="_blank" rel="noopener noreferrer" className="text-teal-600 hover:text-teal-800 underline">llmstxt.org</a>)
                            is a plain Markdown file placed at your domain&apos;s root. It tells LLMs what your website is about,
                            how it&apos;s structured, and which pages are most important—enabling AI models to reason about and cite
                            your site accurately. Think of it as the <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">robots.txt</code> equivalent
                            for the AI era.
                        </p>
                    </div>
                </div>
            )}

            {/* Empty state info section (only shown when no result and not generating) */}
            {!result && !isGenerating && !error && (
                <div className="space-y-6">
                    {/* What is llms.txt? */}
                    <div className="dashboard-card p-6">
                        <h3 className="font-semibold text-gray-900 mb-3">What is llms.txt?</h3>
                        <p className="text-sm text-gray-600 leading-relaxed mb-4">
                            The <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded font-mono">llms.txt</code> standard
                            is a plain Markdown file placed at your domain&apos;s root that tells AI models (ChatGPT, Claude, Gemini)
                            what your website is about, how it&apos;s structured, and which pages are most important.
                            It&apos;s the <strong>SEO robots.txt equivalent for the AI era</strong>.
                        </p>
                        <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                            <p className="text-xs font-mono text-gray-500 mb-2">Example format:</p>
                            <pre className="text-xs font-mono text-gray-700 leading-relaxed">{`# Your Brand Name

> A one-sentence description of what your site is and does.

## Documentation

- [Getting Started](https://example.com/docs): Step-by-step setup guide.
- [API Reference](https://example.com/api): Full REST API documentation.

## Blog

- [Latest Update](https://example.com/blog/update): What's new in v2.0.`}</pre>
                        </div>
                    </div>

                    {/* How it works */}
                    <div className="dashboard-card p-6">
                        <h3 className="font-semibold text-gray-900 mb-4">How It Works</h3>
                        <div className="grid grid-cols-4 gap-4">
                            {[
                                { step: 1, title: "URL Discovery", desc: "We crawl your sitemap, robots.txt, and internal links to find all pages.", icon: Search },
                                { step: 2, title: "Content Extraction", desc: "Each page's content, metadata, and structure are extracted and analyzed.", icon: FileText },
                                { step: 3, title: "AI Analysis", desc: "Claude AI classifies, scores, and summarizes every page for optimal LLM indexing.", icon: Sparkles },
                                { step: 4, title: "File Generation", desc: "A spec-compliant llms.txt file is generated with intelligent sectioning.", icon: Code },
                            ].map((item) => (
                                <div key={item.step} className="text-center p-4 rounded-xl border border-gray-100 bg-gray-50/50">
                                    <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center mx-auto mb-3">
                                        <item.icon className="h-5 w-5 text-teal-600" />
                                    </div>
                                    <div className="text-xs font-bold text-teal-600 mb-1">Step {item.step}</div>
                                    <h4 className="text-sm font-semibold text-gray-900 mb-1">{item.title}</h4>
                                    <p className="text-xs text-gray-500 leading-relaxed">{item.desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
