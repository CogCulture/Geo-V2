"use client";

import { useState, useEffect, Fragment } from "react";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from "@/components/ui/table";
import {
    ChevronDown,
    ChevronRight,
    ExternalLink,
    HelpCircle,
    FileText,
    Bot
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface CitationURL {
    url: string;
    prompt: string;
    llm: string;
    date: string;
}

interface DomainCitation {
    domain: string;
    count: number;
    percentage: number;
    type: string;
    competitors: string[];
    models: string[];
    urls: CitationURL[];
    date: string;
}

interface CitationAnalyticsProps {
    sessionId?: string;
    brandName?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function CitationAnalytics({ sessionId, brandName }: CitationAnalyticsProps) {
    const [data, setData] = useState<DomainCitation[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const ITEMS_PER_PAGE = 20;

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                const token = localStorage.getItem("token");

                let url = "";
                if (brandName) {
                    url = `${API_BASE_URL}/api/analysis/citations/brand/${encodeURIComponent(brandName)}`;
                } else if (sessionId) {
                    url = `${API_BASE_URL}/api/analysis/citations/${sessionId}`;
                } else {
                    return;
                }

                const response = await fetch(url, {
                    headers: {
                        "Authorization": `Bearer ${token}`
                    }
                });

                if (!response.ok) throw new Error("Failed to fetch citations");

                const result = await response.json();
                const fetchedData = result.citations || [];

                // Map backend data to frontend interface (llms -> models)
                const mappedData = fetchedData.map((item: any) => ({
                    ...item,
                    models: item.llms || item.models || [],
                    competitors: item.competitors || []
                }));

                setData(mappedData);
                // Reset page when new data loads
                setCurrentPage(1);
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [sessionId, brandName]);

    // Pagination logic
    const totalPages = Math.ceil(data.length / ITEMS_PER_PAGE);
    const paginatedData = data.slice(
        (currentPage - 1) * ITEMS_PER_PAGE,
        currentPage * ITEMS_PER_PAGE
    );

    const handleNextPage = () => {
        if (currentPage < totalPages) setCurrentPage(prev => prev + 1);
    };

    const handlePrevPage = () => {
        if (currentPage > 1) setCurrentPage(prev => prev - 1);
    };

    const toggleRow = (domain: string) => {
        const newExpanded = new Set(expandedRows);
        if (newExpanded.has(domain)) {
            newExpanded.delete(domain);
        } else {
            newExpanded.add(domain);
        }
        setExpandedRows(newExpanded);
    };

    const formatDate = (dateString: string) => {
        if (!dateString) return "";
        return new Date(dateString).toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric"
        });
    };

    if (loading) {
        return (
            <div className="flex justify-center p-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-500"></div>
            </div>
        );
    }

    if (error) {
        return <div className="p-4 text-red-500">Error: {error}</div>;
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3 border-b border-gray-100 pb-6">
                <div className="p-2 bg-purple-50 rounded-lg text-purple-600">
                    <FileText className="h-6 w-6" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">
                        {brandName ? `${brandName} Citation Repository` : 'Citation Analysis'}
                    </h1>
                    <p className="text-gray-500">
                        {brandName
                            ? `Comprehensive repository of all citations found across various analysis prompts for this brand.`
                            : `Deep dive into where your brand is being cited across different domains for this session.`
                        }
                    </p>
                </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                <Table>
                    <TableHeader className="bg-gray-50/50">
                        <TableRow className="border-b border-gray-100 hover:bg-transparent">
                            <TableHead className="w-12 text-center">#</TableHead>
                            <TableHead>DOMAIN</TableHead>
                            <TableHead className="text-center">TYPE</TableHead>
                            <TableHead className="w-[150px]">
                                <div className="flex items-center gap-1">
                                    COMPETITORS
                                    <TooltipProvider>
                                        <Tooltip>
                                            <TooltipTrigger><HelpCircle className="h-3 w-3 text-gray-400" /></TooltipTrigger>
                                            <TooltipContent>Competitors mentioned in the same context</TooltipContent>
                                        </Tooltip>
                                    </TooltipProvider>
                                </div>
                            </TableHead>
                            <TableHead>
                                <div className="flex items-center gap-1">
                                    CITATIONS
                                    <TooltipProvider>
                                        <Tooltip>
                                            <TooltipTrigger><HelpCircle className="h-3 w-3 text-gray-400" /></TooltipTrigger>
                                            <TooltipContent>Total number of times this domain was cited</TooltipContent>
                                        </Tooltip>
                                    </TooltipProvider>
                                </div>
                            </TableHead>
                            <TableHead>MODELS</TableHead>
                            <TableHead className="text-right">DATE</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {paginatedData.map((row, idx) => {
                            const isExpanded = expandedRows.has(row.domain);
                            const globalIndex = (currentPage - 1) * ITEMS_PER_PAGE + idx + 1;

                            return (
                                <Fragment key={row.domain}>
                                    <TableRow className={cn("group hover:bg-gray-50/50 transition-colors border-b border-gray-100", isExpanded && "bg-gray-50/30")}>
                                        <TableCell className="text-center text-gray-500 font-medium">{globalIndex}.</TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-3">
                                                <span className="font-semibold text-gray-900">{row.domain}</span>
                                                <a href={`https://${row.domain}`} target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-teal-600">
                                                    <ExternalLink className="h-3.5 w-3.5" />
                                                </a>
                                                <button
                                                    onClick={() => toggleRow(row.domain)}
                                                    className={cn(
                                                        "flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded transition-colors",
                                                        isExpanded
                                                            ? "bg-orange-50 text-orange-600 hover:bg-orange-100"
                                                            : "text-orange-500 hover:bg-orange-50"
                                                    )}
                                                >
                                                    {isExpanded ? (
                                                        <>Hide <ChevronDown className="h-3 w-3" /></>
                                                    ) : (
                                                        <>URLs <ChevronRight className="h-3 w-3" /></>
                                                    )}
                                                </button>
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-center">
                                            <Badge variant="secondary" className="bg-gray-100 text-gray-500 font-normal border-gray-200">
                                                {row.type}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            {row.competitors && row.competitors.length > 0 ? (
                                                <div className="flex -space-x-2">
                                                    {row.competitors.slice(0, 3).map((comp, i) => (
                                                        <div key={i} className="h-6 w-6 rounded-full bg-gray-200 border-2 border-white flex items-center justify-center text-[10px] uppercase font-bold text-gray-500" title={comp}>
                                                            {comp[0]}
                                                        </div>
                                                    ))}
                                                    {row.competitors.length > 3 && (
                                                        <div className="h-6 w-6 rounded-full bg-gray-100 border-2 border-white flex items-center justify-center text-[10px] text-gray-500 font-medium">
                                                            +{row.competitors.length - 3}
                                                        </div>
                                                    )}
                                                </div>
                                            ) : (
                                                <span className="text-gray-400 text-sm">None</span>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-2">
                                                <span className="font-bold text-gray-900">×{row.count}</span>
                                                <span className="text-xs text-gray-500">({row.percentage}%)</span>
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-1">
                                                {(row.models || []).slice(0, 3).map((model, i) => (
                                                    <div key={i} className="h-5 w-5 rounded-md bg-white border border-gray-200 flex items-center justify-center text-[10px] text-gray-500" title={model}>
                                                        {model[0]}
                                                    </div>
                                                ))}
                                                {(row.models || []).length > 3 && (
                                                    <span className="text-xs text-gray-500">+{(row.models || []).length - 3}</span>
                                                )}
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-right text-gray-500 text-sm">
                                            {formatDate(row.date)}
                                        </TableCell>
                                    </TableRow>

                                    {isExpanded && (
                                        <TableRow className="bg-gray-50 hover:bg-gray-50">
                                            <TableCell colSpan={7} className="p-0">
                                                <div className="px-12 py-6 space-y-4 border-l-4 border-teal-200 ml-6 my-2 bg-white rounded-r-lg shadow-sm w-[95%]">
                                                    <div className="flex items-center gap-2 mb-4">
                                                        <h4 className="font-semibold text-gray-900">Unique URLs cited for {row.domain}</h4>
                                                        <Badge variant="outline" className="bg-gray-50 text-gray-600 border-gray-200">
                                                            {row.urls.length} Unique URLs
                                                        </Badge>
                                                    </div>

                                                    <div className="space-y-3">
                                                        {row.urls.map((urlItem, idx) => (
                                                            <div key={idx} className="p-4 rounded-xl border border-gray-100 bg-white hover:border-gray-200 transition-colors group/card">
                                                                <div className="flex justify-between items-start gap-4">
                                                                    <div className="space-y-3 flex-1">
                                                                        <a href={urlItem.url} target="_blank" rel="noopener noreferrer" className="text-sm font-medium text-teal-600 hover:text-teal-700 hover:underline break-all block">
                                                                            {urlItem.url}
                                                                        </a>

                                                                        <div className="flex items-center gap-3 flex-wrap">
                                                                            <div className="text-xs text-gray-400 font-medium bg-gray-50 px-2 py-1 rounded">
                                                                                {formatDate(urlItem.date)}
                                                                            </div>

                                                                            <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-emerald-50 text-emerald-700 text-xs font-medium border border-emerald-100">
                                                                                <Bot className="h-3 w-3" />
                                                                                {urlItem.llm}
                                                                            </div>

                                                                            {urlItem.prompt && (
                                                                                <div className="px-2 py-1 rounded-md bg-orange-50 text-orange-700 text-xs border border-orange-100 truncate max-w-[400px]" title={urlItem.prompt}>
                                                                                    {urlItem.prompt}
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                    </div>

                                                                    <a href={urlItem.url} target="_blank" rel="noopener noreferrer" className="text-gray-300 hover:text-teal-600 opacity-0 group-hover/card:opacity-100 transition-opacity">
                                                                        <ExternalLink className="h-4 w-4" />
                                                                    </a>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    )}
                                </Fragment>
                            );
                        })}

                        {data.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={7} className="h-32 text-center text-gray-500">
                                    No citations found for this session.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between px-2 py-4">
                    <p className="text-sm text-gray-500">
                        Showing <span className="font-medium">{(currentPage - 1) * ITEMS_PER_PAGE + 1}</span> to{" "}
                        <span className="font-medium">
                            {Math.min(currentPage * ITEMS_PER_PAGE, data.length)}
                        </span>{" "}
                        of <span className="font-medium">{data.length}</span> results
                    </p>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handlePrevPage}
                            disabled={currentPage === 1}
                            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            Previous
                        </button>
                        <div className="flex items-center gap-1 px-3">
                            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                // Simple logic to show a few page numbers
                                let pageNum = i + 1;
                                if (totalPages > 5 && currentPage > 3) {
                                    pageNum = currentPage - 3 + i + 1;
                                    if (pageNum > totalPages) pageNum = totalPages - (4 - i);
                                }
                                if (pageNum < 1) return null;

                                return (
                                    <button
                                        key={pageNum}
                                        onClick={() => setCurrentPage(pageNum)}
                                        className={cn(
                                            "w-8 h-8 flex items-center justify-center rounded-md text-sm transition-all",
                                            currentPage === pageNum
                                                ? "bg-teal-500 text-white font-bold"
                                                : "text-gray-600 hover:bg-gray-100"
                                        )}
                                    >
                                        {pageNum}
                                    </button>
                                );
                            })}
                        </div>
                        <button
                            onClick={handleNextPage}
                            disabled={currentPage === totalPages}
                            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            Next
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
