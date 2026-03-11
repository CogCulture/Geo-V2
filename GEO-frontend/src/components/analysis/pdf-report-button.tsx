import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { useState } from "react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import html2canvas from "html2canvas";
import type { AnalysisResults as AnalysisResultsType } from "@shared/schema";

interface PDFReportButtonProps {
  results: AnalysisResultsType;
  sessionId: string;
}

export function PDFReportButton({ results, sessionId }: PDFReportButtonProps) {
  const [isGenerating, setIsGenerating] = useState(false);

  // --- CONFIGURATION ---
  const CONFIG = {
    colors: {
      primary: [0, 0, 0] as [number, number, number], // Black
      secondary: [80, 80, 80] as [number, number, number], // Dark Gray
      accent: [220, 220, 220] as [number, number, number], // Light Gray (lines/borders)
      text: [40, 40, 40] as [number, number, number],
      muted: [120, 120, 120] as [number, number, number],
      bg: [255, 255, 255] as [number, number, number],
    },
    margins: {
      top: 20,
      bottom: 20,
      left: 20,
      right: 20,
    },
    fonts: {
      head: "helvetica",
      body: "helvetica",
    },
  };

  // --- HELPERS ---

  const captureChart = async (elementId: string): Promise<string | null> => {
    try {
      const element = document.getElementById(elementId);
      if (!element) return null;
      // Capture at high scale for print quality
      const canvas = await html2canvas(element, {
        scale: 3,
        backgroundColor: "#ffffff",
        logging: false,
        useCORS: true,
      });
      return canvas.toDataURL("image/png");
    } catch (error) {
      console.error(`Error capturing ${elementId}:`, error);
      return null;
    }
  };

  const loadImageAsBase64 = (path: string): Promise<string> => {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = "Anonymous";
      img.src = path;
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext("2d");
        if (!ctx) return reject("Canvas error");
        ctx.drawImage(img, 0, 0);
        resolve(canvas.toDataURL("image/png"));
      };
      img.onerror = reject;
    });
  };

  // --- MAIN GENERATOR ---

  const generatePDF = async () => {
    setIsGenerating(true);

    try {
      const pdf = new jsPDF("p", "mm", "a4");
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const margin = CONFIG.margins.left;
      const contentWidth = pageWidth - margin * 2;

      // Helper: Draw Header on content pages
      const drawPageHeader = (title: string) => {
        pdf.setFillColor(CONFIG.colors.primary[0], CONFIG.colors.primary[1], CONFIG.colors.primary[2]);
        // Small accent bar on left
        pdf.rect(0, 15, 6, 12, "F");

        pdf.setFont(CONFIG.fonts.head, "bold");
        pdf.setFontSize(16);
        pdf.setTextColor(CONFIG.colors.primary[0], CONFIG.colors.primary[1], CONFIG.colors.primary[2]);
        pdf.text(title.toUpperCase(), margin, 24);

        // Divider line
        pdf.setDrawColor(CONFIG.colors.accent[0], CONFIG.colors.accent[1], CONFIG.colors.accent[2]);
        pdf.line(margin, 30, pageWidth - margin, 30);
      };

      // Helper: Draw Footer
      const addFooters = () => {
        const totalPages = pdf.getNumberOfPages();
        for (let i = 1; i <= totalPages; i++) {
          pdf.setPage(i);
          if (i === 1) continue; // Skip cover

          pdf.setFontSize(8);
          pdf.setTextColor(CONFIG.colors.muted[0], CONFIG.colors.muted[1], CONFIG.colors.muted[2]);

          // Line above footer
          pdf.setDrawColor(230, 230, 230);
          pdf.line(margin, pageHeight - 15, pageWidth - margin, pageHeight - 15);

          const dateStr = new Date().toLocaleDateString();
          pdf.text(`GEO Analysis • ${dateStr}`, margin, pageHeight - 10);
          pdf.text(`Page ${i} of ${totalPages}`, pageWidth - margin, pageHeight - 10, { align: "right" });
        }
      };

      // ======================== 1. COVER PAGE ============================

      // LOGO: Top Left
      try {
        const logo = await loadImageAsBase64("/logo.png");
        if (logo) {
          pdf.addImage(logo, "PNG", margin, margin, 60, 20);
        }
      } catch (e) {
        console.warn("Logo not found, skipping");
      }

      // Title Block
      let yPos = 100;

      pdf.setFont(CONFIG.fonts.head, "bold");
      pdf.setFontSize(42);
      pdf.setTextColor(CONFIG.colors.primary[0], CONFIG.colors.primary[1], CONFIG.colors.primary[2]);
      pdf.text("Brand Visibility", margin, yPos);

      pdf.setFontSize(42);
      pdf.setTextColor(CONFIG.colors.secondary[0], CONFIG.colors.secondary[1], CONFIG.colors.secondary[2]);
      pdf.text("Analysis Report", margin, yPos + 16);

      // Accent Line
      yPos += 30;
      pdf.setDrawColor(0, 0, 0);
      pdf.setLineWidth(1);
      pdf.line(margin, yPos, margin + 20, yPos);

      // Brand Info
      yPos += 15;
      pdf.setFontSize(14);
      pdf.setTextColor(CONFIG.colors.muted[0], CONFIG.colors.muted[1], CONFIG.colors.muted[2]);
      pdf.text("PREPARED FOR:", margin, yPos);

      yPos += 8;
      pdf.setFontSize(24);
      pdf.setTextColor(CONFIG.colors.primary[0], CONFIG.colors.primary[1], CONFIG.colors.primary[2]);
      pdf.text(results.brand_name, margin, yPos);

      // Metadata
      const bottomY = pageHeight - 40;
      pdf.setFontSize(10);
      pdf.setTextColor(CONFIG.colors.muted[0], CONFIG.colors.muted[1], CONFIG.colors.muted[2]);

      pdf.text("SESSION ID", margin, bottomY);
      pdf.text("DATE GENERATED", margin + 60, bottomY);

      pdf.setFontSize(10);
      pdf.setTextColor(CONFIG.colors.text[0], CONFIG.colors.text[1], CONFIG.colors.text[2]);
      pdf.text(sessionId, margin, bottomY + 6);
      pdf.text(new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }), margin + 60, bottomY + 6);


      // ==================== 2. EXECUTIVE SUMMARY ====================
      pdf.addPage();
      drawPageHeader("Executive Summary");
      yPos = 45;

      // Intro Text
      pdf.setFontSize(11);
      pdf.setTextColor(CONFIG.colors.text[0], CONFIG.colors.text[1], CONFIG.colors.text[2]);
      pdf.text(`An AI-driven analysis of brand presence for ${results.brand_name}.`, margin, yPos);
      yPos += 15;

      // --- Metrics Grid ---
      const cardGap = 8;
      const cardWidth = (contentWidth - cardGap) / 2;
      const cardHeight = 35;

      const metrics = [
        { label: "Analyzed Prompts", value: results.num_prompts || 0 },
        { label: "Brand Mentions", value: results.average_mentions || 0 },
        { label: "Avg. Position", value: (results.average_position || 0).toFixed(1) },
        { label: "Visibility Score", value: `${(results.average_visibility_score || 0).toFixed(1)}%` },
      ];

      metrics.forEach((m, i) => {
        const col = i % 2;
        const row = Math.floor(i / 2);
        const x = margin + col * (cardWidth + cardGap);
        const y = yPos + row * (cardHeight + cardGap);

        pdf.setFillColor(248, 248, 248);
        pdf.setDrawColor(230, 230, 230);
        pdf.roundedRect(x, y, cardWidth, cardHeight, 2, 2, "FD");

        pdf.setFontSize(9);
        pdf.setTextColor(CONFIG.colors.muted[0], CONFIG.colors.muted[1], CONFIG.colors.muted[2]);
        pdf.text(m.label.toUpperCase(), x + 6, y + 10);

        pdf.setFontSize(18);
        pdf.setFont(CONFIG.fonts.head, "bold");
        pdf.setTextColor(CONFIG.colors.primary[0], CONFIG.colors.primary[1], CONFIG.colors.primary[2]);
        pdf.text(String(m.value), x + 6, y + 24);
      });

      yPos += (cardHeight * 2) + cardGap + 20;

      // --- Key Insights ---
      pdf.setFontSize(14);
      pdf.setFont(CONFIG.fonts.head, "bold");
      pdf.text("Key Findings", margin, yPos);
      yPos += 10;

      pdf.setFont(CONFIG.fonts.body, "normal");
      pdf.setFontSize(10);
      pdf.setTextColor(CONFIG.colors.text[0], CONFIG.colors.text[1], CONFIG.colors.text[2]);

      const mentionRate = results.num_prompts > 0
        ? ((results.average_mentions / results.num_prompts) * 100).toFixed(1)
        : 0;

      const insights = [
        `• Your brand appeared in ${mentionRate}% of the generative AI responses analyzed.`,
        `• On average, when mentioned, your brand ranks at position ${(results.average_position || 0).toFixed(1)}.`,
        `• The overall visibility health score is ${(results.average_visibility_score || 0).toFixed(1)}%, calculated based on frequency and ranking.`,
      ];

      insights.forEach((insight) => {
        pdf.text(insight, margin, yPos);
        yPos += 8;
      });

      // ==================== 3. SHARE OF VOICE ====================
      if (results.share_of_voice && results.share_of_voice.length > 0) {
        pdf.addPage();
        drawPageHeader("Competitive Landscape");
        yPos = 40;

        // 1. CHART CAPTURE
        // Ensure "sov-chart-container" is the ID in share-of-voice-chart.tsx
        const sovChartImg = await captureChart('sov-chart-container');
        if (sovChartImg) {
          const imgHeight = 100;
          pdf.addImage(sovChartImg, 'PNG', margin, yPos, contentWidth, imgHeight);
          yPos += imgHeight + 10;
        }

        // 2. TABLE (Clean: No raw mentions)
        const sovData = results.share_of_voice.map((item, idx) => [
          idx + 1,
          item.brand || 'Unknown',
          `${(item.percentage || 0).toFixed(1)}%`
        ]);

        autoTable(pdf, {
          startY: yPos,
          head: [['Rank', 'Brand', 'Share of Voice']],
          body: sovData,
          theme: 'plain',
          headStyles: {
            fillColor: CONFIG.colors.primary,
            textColor: 255,
            fontStyle: 'bold',
            halign: 'left',
            cellPadding: 4
          },
          bodyStyles: {
            textColor: CONFIG.colors.text,
            cellPadding: 4,
            lineColor: 240,
            lineWidth: { bottom: 0.1 }
          },
          columnStyles: {
            0: { cellWidth: 20 },
            2: { halign: 'right' }
          },
          margin: { left: margin, right: margin }
        });
      }


      // ==================== 4. SOURCE ANALYSIS ====================
      if (results.domain_citations && results.domain_citations.length > 0) {
        pdf.addPage();
        drawPageHeader("Source Analysis");
        yPos = 40;

        pdf.setFontSize(10);
        pdf.setFont(CONFIG.fonts.body, "normal");
        pdf.text("Top domains cited by AI models:", margin, yPos);
        yPos += 10;

        const citationData = results.domain_citations.slice(0, 15).map((item, idx) => [
          idx + 1,
          item.domain || 'Unknown',
          item.citation_count || 0,
          `${(item.percentage || 0).toFixed(1)}%`
        ]);

        autoTable(pdf, {
          startY: yPos,
          head: [['#', 'Domain Source', 'Citations', 'Freq.']],
          body: citationData,
          theme: 'grid',
          headStyles: { fillColor: CONFIG.colors.secondary, textColor: 255, fontStyle: 'bold' },
          styles: { fontSize: 9, cellPadding: 3 },
          columnStyles: {
            0: { cellWidth: 15, halign: 'center' },
            2: { halign: 'center' },
            3: { halign: 'center' }
          },
          margin: { left: margin, right: margin }
        });
      }


      // ==================== 5. PROMPT LOG ====================
      if (results.llm_responses && results.llm_responses.length > 0) {
        pdf.addPage();
        drawPageHeader("Prompt Analysis Log");
        yPos = 40;

        const promptsData = results.llm_responses.map((response, idx) => {
          const promptText = response.prompt || "—";
          const cleanPrompt = promptText.length > 150 ? promptText.substring(0, 147) + "..." : promptText;
          const mentioned = (response.visibility_score || 0) > 0 ? "Yes" : "No";

          return [
            idx + 1,
            cleanPrompt,
            response.llm_name || "Unknown",
            mentioned
          ];
        });

        autoTable(pdf, {
          startY: yPos,
          head: [['#', 'Prompt Query', 'Model', 'Mentioned']],
          body: promptsData,
          theme: 'plain',
          headStyles: {
            fillColor: CONFIG.colors.primary,
            textColor: 255,
            halign: 'left'
          },
          bodyStyles: {
            lineColor: 230,
            lineWidth: { bottom: 0.1 }
          },
          columnStyles: {
            0: { cellWidth: 15, halign: 'center' },
            1: { cellWidth: 'auto' },
            2: { cellWidth: 30 },
            3: { cellWidth: 25, halign: 'center' }
          },
          margin: { left: margin, right: margin }
        });
      }

      // Finalize
      addFooters();

      const fileName = `Report_${results.brand_name.replace(/\s+/g, "_")}_${new Date().toISOString().split("T")[0]}.pdf`;
      pdf.save(fileName);

    } catch (error) {
      console.error("PDF Gen Error:", error);
      alert("Failed to generate report.");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <Button
      onClick={generatePDF}
      disabled={isGenerating}
      className="bg-teal-500 hover:bg-teal-600 text-white gap-2 shadow-md"
    >
      <Download className="h-4 w-4" />
      {isGenerating ? "Generating..." : "Download Report"}
    </Button>
  );
}