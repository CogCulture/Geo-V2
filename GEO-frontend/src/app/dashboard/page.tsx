"use client";

import { ProjectsWindow } from "@/components/dashboard/projects-window";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { LogIn } from "lucide-react";
import { Header } from "@/components/layout/header";

export default function DashboardPage() {
    const router = useRouter();
    const { logout } = useAuth();

    const handleSelectProject = (projectId: string) => {
        router.push(`/dashboard/${encodeURIComponent(projectId)}`);
    };

    const handleCreateProject = () => {
        router.push("/dashboard/analysis");
    };


    return (
        <div className="min-h-screen bg-gray-50/50">
            <Header />
            <main className="max-w-7xl mx-auto px-6 py-12">
                <ProjectsWindow
                    onSelectProject={handleSelectProject}
                    onCreateProject={handleCreateProject}
                />
            </main>
        </div>
    );
}
