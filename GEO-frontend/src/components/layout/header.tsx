"use client";

import { Zap } from "lucide-react";
import Image from "next/image";
import { UserProfileMenu } from "./user-profile-menu";

export function Header() {
    return (
        <header className="sticky top-0 z-50 w-full bg-white/90 backdrop-blur-md border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Image
                        src="/logo.png"
                        alt="CogCulture"
                        width={130}
                        height={36}
                        className="object-contain h-9 w-auto"
                        priority
                    />
                </div>
                <div className="flex items-center gap-4">
                    <a href="/pricing" className="text-sm text-gray-600 hover:text-gray-900 font-medium transition-colors flex items-center gap-1.5">
                        <Zap className="h-4 w-4 text-amber-500" />
                        Pricing
                    </a>
                    <UserProfileMenu />
                </div>
            </div>
        </header>
    );
}
