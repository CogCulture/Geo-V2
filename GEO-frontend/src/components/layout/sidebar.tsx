import { LayoutDashboard, ListTodo, LogOut, Settings, Layout, Users, ChevronDown, ChevronRight, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useRouter } from "next/navigation";

interface SidebarProps {
  activeTab: 'overview' | 'prompts' | 'competitors' | 'citations' | 'llms-txt';
  onTabChange: (tab: 'overview' | 'prompts' | 'competitors' | 'citations') => void;
  onProjectsClick: () => void;
  onLogout: () => void;
  email?: string;
}

export function Sidebar({ activeTab, onTabChange, onProjectsClick, onLogout, email }: SidebarProps) {
  const [projectsOpen, setProjectsOpen] = useState(false);
  const [analyticsOpen, setAnalyticsOpen] = useState(true);
  const [toolsOpen, setToolsOpen] = useState(true);
  const router = useRouter();

  const navItems = [
    { key: 'overview' as const, label: 'Overview', icon: LayoutDashboard },
    { key: 'prompts' as const, label: 'Prompts & Cohorts', icon: ListTodo },
    { key: 'competitors' as const, label: 'Competitors', icon: Users },
    { key: 'citations' as const, label: 'Citation Table', icon: ListTodo },
  ];

  const toolItems = [
    { key: 'llms-txt' as const, label: 'LLMs.txt Generator', icon: FileText },
  ];

  return (
    <div className="w-44 h-screen bg-white border-r border-gray-200 flex flex-col fixed left-0 top-0 z-40">
      {/* Logo */}
      <div className="px-3 py-3 border-b border-gray-200">
        <div className="flex items-center gap-2 cursor-pointer" onClick={onProjectsClick}>
          <img src="/logo.png" alt="CogCulture" className="h-7 w-auto object-contain"
            onError={(e) => {
              e.currentTarget.style.display = 'none';
              e.currentTarget.parentElement!.innerHTML = '<span class="font-extrabold text-base tracking-tighter text-gray-900">CC</span>';
            }} />
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        <p className="px-2 text-[9px] font-semibold text-gray-400 uppercase tracking-widest mb-1">General</p>

        <Button variant="ghost" onClick={() => setProjectsOpen(!projectsOpen)}
          className="w-full justify-between gap-2 h-8 text-xs font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900">
          <span className="flex items-center gap-2"><Layout className="h-3.5 w-3.5" />Projects</span>
          {projectsOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </Button>

        {projectsOpen && (
          <Button variant="ghost" onClick={onProjectsClick}
            className="w-full justify-start gap-1.5 h-7 font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-900 pl-6 text-xs">
            All Projects
          </Button>
        )}

        <p className="px-2 text-[9px] font-semibold text-gray-400 uppercase tracking-widest mb-1 mt-4">Analytics</p>

        <Button variant="ghost" onClick={() => setAnalyticsOpen(!analyticsOpen)}
          className="w-full justify-between gap-2 h-8 text-xs font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 mb-0.5">
          <span className="flex items-center gap-2"><Settings className="h-3.5 w-3.5" />Analytics</span>
          {analyticsOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </Button>

        {analyticsOpen && (
          <div className="space-y-0.5">
            {navItems.map((item) => (
              <Button key={item.key} variant="ghost" onClick={() => onTabChange(item.key)}
                className={cn(
                  "w-full justify-start gap-1.5 h-7 font-medium pl-6 text-xs transition-all overflow-hidden",
                  activeTab === item.key
                    ? "bg-teal-50 text-teal-600 hover:bg-teal-100 hover:text-teal-700 border-l-2 border-teal-500 rounded-l-none"
                    : "text-gray-500 hover:bg-gray-100 hover:text-gray-900"
                )}>
                <item.icon className="h-3.5 w-3.5 flex-shrink-0" />
                <span className="truncate">{item.label}</span>
              </Button>
            ))}
          </div>
        )}

        {/* Tools Section */}
        <p className="px-2 text-[9px] font-semibold text-gray-400 uppercase tracking-widest mb-1 mt-4">Tools</p>

        <Button variant="ghost" onClick={() => setToolsOpen(!toolsOpen)}
          className="w-full justify-between gap-2 h-8 text-xs font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 mb-0.5">
          <span className="flex items-center gap-2"><FileText className="h-3.5 w-3.5" />Free Tools</span>
          {toolsOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </Button>

        {toolsOpen && (
          <div className="space-y-0.5">
            {toolItems.map((item) => (
              <Button key={item.key} variant="ghost"
                onClick={() => router.push("/dashboard/llms-txt")}
                className={cn(
                  "w-full justify-start gap-1.5 h-7 font-medium pl-6 text-xs transition-all overflow-hidden",
                  activeTab === item.key
                    ? "bg-teal-50 text-teal-600 hover:bg-teal-100 hover:text-teal-700 border-l-2 border-teal-500 rounded-l-none"
                    : "text-gray-500 hover:bg-gray-100 hover:text-gray-900"
                )}>
                <item.icon className="h-3.5 w-3.5 flex-shrink-0" />
                <span className="truncate">{item.label}</span>
              </Button>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-2 border-t border-gray-200">
        <button className="w-full flex items-center gap-2 px-2 py-2 rounded-lg text-gray-500 hover:text-red-600 hover:bg-red-50 transition-all group" onClick={onLogout}>
          <div className="h-6 w-6 rounded-full bg-gray-100 flex items-center justify-center group-hover:bg-red-100 transition-colors">
            <LogOut className="h-3 w-3" />
          </div>
          <span className="text-xs font-medium">Sign Out</span>
        </button>
      </div>
    </div>
  );
}