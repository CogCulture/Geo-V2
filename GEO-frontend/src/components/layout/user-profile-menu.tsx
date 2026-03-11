"use client";

import { LogOut, Settings, User, HelpCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuGroup,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    Avatar,
    AvatarFallback,
    AvatarImage,
} from "@/components/ui/avatar";

export function UserProfileMenu() {
    const router = useRouter();
    const { logout, email, subscription } = useAuth();

    const handleLogout = () => {
        logout();
        router.push("/");
    };

    const initials = email ? email.substring(0, 2).toUpperCase() : "U";
    const displayName = email ? email.split('@')[0] : "User";

    // Capitalize plan name correctly (e.g., "Lite Plan" instead of "lite plan")
    const formatPlanName = (name: string) => {
        return name.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ');
    };

    const displayPlan = subscription?.is_active && subscription?.subscription_plan
        ? formatPlanName(subscription.subscription_plan)
        : "Free Plan";

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <button className="outline-none rounded-full ring-offset-2 ring-offset-white focus:ring-2 focus:ring-teal-400 transition-all">
                    <Avatar className="h-10 w-10 border border-gray-200 hover:border-teal-400 transition-colors">
                        <AvatarImage src="" alt={displayName} />
                        <AvatarFallback className="bg-teal-500 text-white font-medium">
                            {initials}
                        </AvatarFallback>
                    </Avatar>
                </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-80 p-2 bg-white border-gray-200 shadow-xl" align="end">
                <div className="flex items-center gap-3 p-3">
                    <Avatar className="h-12 w-12 border border-gray-200">
                        <AvatarImage src="" alt={displayName} />
                        <AvatarFallback className="bg-teal-500 text-white text-lg font-medium">
                            {initials}
                        </AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col space-y-0.5">
                        <p className="text-sm font-bold text-gray-900 capitalize">{displayName.replace('.', ' ')}</p>
                        <p className="text-xs text-gray-500 truncate max-w-[180px]">{email}</p>
                        <p className="text-xs text-teal-600 font-medium pt-0.5">{displayPlan}</p>
                    </div>
                </div>

                <DropdownMenuSeparator className="my-2 bg-gray-100" />

                <DropdownMenuGroup>
                    <DropdownMenuItem className="cursor-pointer gap-3 p-3 focus:bg-gray-50 rounded-md group">
                        <div className="p-2 bg-gray-50 rounded-full group-hover:bg-gray-100 transition-colors border border-transparent group-hover:border-gray-200">
                            <User className="h-4 w-4 text-gray-500 group-hover:text-teal-600" />
                        </div>
                        <div className="flex flex-col gap-0.5">
                            <span className="text-sm font-medium text-gray-900">Profile</span>
                            <span className="text-xs text-gray-500">View and edit your profile</span>
                        </div>
                    </DropdownMenuItem>

                    <DropdownMenuItem className="cursor-pointer gap-3 p-3 focus:bg-gray-50 rounded-md group">
                        <div className="p-2 bg-gray-50 rounded-full group-hover:bg-gray-100 transition-colors border border-transparent group-hover:border-gray-200">
                            <Settings className="h-4 w-4 text-gray-500 group-hover:text-teal-600" />
                        </div>
                        <div className="flex flex-col gap-0.5">
                            <span className="text-sm font-medium text-gray-900">Settings</span>
                            <span className="text-xs text-gray-500">Preferences and configuration</span>
                        </div>
                    </DropdownMenuItem>

                    <DropdownMenuItem className="cursor-pointer gap-3 p-3 focus:bg-gray-50 rounded-md group">
                        <div className="p-2 bg-gray-50 rounded-full group-hover:bg-gray-100 transition-colors border border-transparent group-hover:border-gray-200">
                            <HelpCircle className="h-4 w-4 text-gray-500 group-hover:text-teal-600" />
                        </div>
                        <div className="flex flex-col gap-0.5">
                            <span className="text-sm font-medium text-gray-900">Help & Support</span>
                            <span className="text-xs text-gray-500">Documentation and assistance</span>
                        </div>
                    </DropdownMenuItem>
                </DropdownMenuGroup>

                <DropdownMenuSeparator className="my-2 bg-gray-100" />

                <DropdownMenuItem
                    className="cursor-pointer gap-3 p-3 text-red-500 focus:text-red-600 focus:bg-red-50 rounded-md group"
                    onClick={handleLogout}
                >
                    <div className="p-2 bg-red-50 rounded-full group-hover:bg-red-100 transition-colors border border-transparent group-hover:border-red-200">
                        <LogOut className="h-4 w-4 text-red-500" />
                    </div>
                    <span className="text-sm font-medium">Sign Out</span>
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
