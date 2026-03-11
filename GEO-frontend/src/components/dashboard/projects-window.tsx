"use client";

import { useState, useEffect } from "react";
import { Plus, Layout, Calendar, Globe, Briefcase, ChevronRight, Search, Trash2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Project {
    id: string;
    name: string;
    website_url?: string;
    industry?: string;
    update_frequency: string;
    is_active: boolean;
    created_at: string;
    last_sync_at?: string;
}

interface ProjectsWindowProps {
    onSelectProject: (projectId: string) => void;
    onCreateProject: () => void;
}

const FRONTEND_PLAN_LIMITS: Record<string, { max_projects: number }> = {
    "free": { max_projects: 1 },
    "lite plan": { max_projects: 2 },
    "growth plan": { max_projects: 4 },
    "custom plan": { max_projects: 8 },
    "pro plan": { max_projects: 8 },
};

export function ProjectsWindow({ onSelectProject, onCreateProject }: ProjectsWindowProps) {
    const { subscription } = useAuth();
    const [projects, setProjects] = useState<Project[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [projectToDelete, setProjectToDelete] = useState<string | null>(null);

    const planName = subscription.subscription_plan?.toLowerCase() || "free";
    const limits = FRONTEND_PLAN_LIMITS[planName] || FRONTEND_PLAN_LIMITS["free"];
    const isLimitReached = projects.length >= limits.max_projects;

    useEffect(() => {
        fetchProjects();
    }, []);

    // ... (rest as is)
    const fetchProjects = async () => {
        setIsLoading(true);
        try {
            const token = localStorage.getItem("token");
            const response = await fetch(`${API_BASE_URL}/api/projects`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (response.ok) {
                const data = await response.json();
                setProjects(data.projects || []);
            }
        } catch (error) {
            console.error("Error fetching projects:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const filteredProjects = projects.filter(p =>
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.industry?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const handleDeleteProject = async () => {
        if (!projectToDelete) return;

        try {
            const token = localStorage.getItem("token");
            const response = await fetch(`${API_BASE_URL}/api/projects/${projectToDelete}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (response.ok) {
                setProjects(prev => prev.filter(p => p.id !== projectToDelete));
                setProjectToDelete(null);
            } else {
                console.error("Failed to delete project");
            }
        } catch (error) {
            console.error("Error deleting project:", error);
        }
    };

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-500"></div>
                <p className="text-gray-500 font-medium">Loading your projects...</p>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-gray-900">Brand Projects</h1>
                    <p className="text-gray-500 mt-1">Manage and monitor your brand visibility across all your projects.</p>
                </div>
                <div className="flex items-center gap-3">
                    {isLimitReached && (
                        <div className="hidden md:flex flex-col items-end mr-2">
                            <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50 rounded-md py-0.5">
                                {planName.toUpperCase()} Limit: {projects.length}/{limits.max_projects} used
                            </Badge>
                            <p className="text-[10px] text-gray-400 mt-1">Upgrade to add more</p>
                        </div>
                    )}
                    <Button
                        onClick={onCreateProject}
                        className={`shadow-md transition-all ${isLimitReached ? "bg-gray-200 text-gray-400 cursor-not-allowed hover:bg-gray-200" : "bg-teal-500 text-white hover:bg-teal-600 hover:scale-105"}`}
                        disabled={isLimitReached}
                    >
                        <Plus className="h-4 w-4 mr-2" />
                        Create New Project
                    </Button>
                </div>
            </div>

            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                    placeholder="Search projects by name or industry..."
                    className="pl-10 h-12 bg-white border-gray-200 text-gray-900 placeholder:text-gray-400 shadow-sm focus:border-teal-400 focus:ring-teal-400/20"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
            </div>

            {filteredProjects.length === 0 ? (
                <Card className="border-dashed border-2 border-gray-200 py-12 bg-gray-50/50">
                    <CardContent className="flex flex-col items-center justify-center text-center space-y-4">
                        <div className="h-16 w-16 rounded-full bg-gray-100 flex items-center justify-center">
                            <Layout className="h-8 w-8 text-gray-400" />
                        </div>
                        <div className="max-w-xs">
                            <h3 className="text-lg font-semibold text-gray-900">No projects found</h3>
                            <p className="text-gray-500 mt-2">
                                {searchQuery ? "Try adjusting your search terms." : "You haven't created any brand projects yet. Get started by creating your first one."}
                            </p>
                        </div>
                        {!searchQuery && (
                            <Button onClick={onCreateProject} variant="outline" className="mt-4 border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-900">
                                Create My First Project
                            </Button>
                        )}
                    </CardContent>
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredProjects.map((project) => (
                        <Card
                            key={project.id}
                            className="group hover:shadow-lg transition-all duration-300 border-gray-100 bg-white overflow-hidden cursor-pointer"
                            onClick={() => onSelectProject(project.id)}
                        >
                            <CardHeader className="pb-4">
                                <div className="flex justify-between items-start">
                                    <div className="h-12 w-12 rounded-xl bg-gray-50 flex items-center justify-center text-gray-500 group-hover:bg-teal-50 group-hover:text-teal-600 transition-colors duration-300 border border-gray-100">
                                        <Briefcase className="h-6 w-6" />
                                    </div>
                                    <Badge variant={project.is_active ? "default" : "secondary"} className={project.is_active ? "bg-emerald-50 text-emerald-600 border border-emerald-200" : "bg-gray-100 text-gray-500"}>
                                        {project.is_active ? "Active" : "Paused"}
                                    </Badge>
                                </div>
                                <CardTitle className="mt-4 text-xl text-gray-900 group-hover:text-teal-600 transition-colors">{project.name}</CardTitle>
                                <CardDescription className="flex items-center gap-1 mt-1 text-gray-500">
                                    <Globe className="h-3 w-3" />
                                    {project.website_url || "No website link"}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="pb-4 space-y-3">
                                <div className="flex items-center text-sm text-gray-600 gap-2">
                                    <Calendar className="h-4 w-4 text-gray-400" />
                                    <span>Syncs every {project.update_frequency}</span>
                                </div>
                                {project.industry && (
                                    <div className="flex items-center text-sm text-gray-600 gap-2">
                                        <div className="h-1 w-1 rounded-full bg-gray-400 ml-1.5 mr-1" />
                                        <span>{project.industry}</span>
                                    </div>
                                )}
                            </CardContent>
                            <CardFooter className="pt-4 border-t border-gray-50 bg-gray-50/30 group-hover:bg-white transition-colors relative">
                                <div className="flex justify-between items-center w-full">
                                    <span className="text-xs text-gray-400">
                                        Created {new Date(project.created_at).toLocaleDateString()}
                                    </span>
                                    <div className="flex items-center gap-3">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-8 w-8 text-gray-400 hover:text-red-600 hover:bg-red-50"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setProjectToDelete(project.id);
                                            }}
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                        <div className="flex items-center text-sm font-semibold text-teal-600 opacity-0 group-hover:opacity-100 translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                            Open Dashboard
                                            <ChevronRight className="h-4 w-4 ml-1" />
                                        </div>
                                    </div>
                                </div>
                            </CardFooter>
                        </Card>
                    ))}
                </div>
            )}


            <AlertDialog open={!!projectToDelete} onOpenChange={(open) => !open && setProjectToDelete(null)}>
                <AlertDialogContent className="bg-white border-gray-200">
                    <AlertDialogHeader>
                        <AlertDialogTitle>Are you sure that you want to delete this project completely?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone. This will permanently delete your project and remove all data associated with it from our servers.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={handleDeleteProject} className="bg-red-600 hover:bg-red-700 text-white">
                            Delete Project
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
