"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, Edit2, FolderOpen, MoreVertical, PlusCircle, Trash2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useSidebar } from "@/context/SidebarContext";
import {
    buildBrandChatHref,
    buildBrandWorkspaceHref,
    resolveBrandByRouteKey,
} from "@/lib/brand-routing";
import { sidebarItems } from "@/lib/sidebarItems";
import { cn } from "@/lib/utils";
import { useRBAC } from "@/hooks/useRBAC";
import { useBrands } from "@/hooks/useBrands";
import {
    useChatSessions,
    useCreateChatSession,
    useDeleteChatSession,
    useUpdateChatSession,
} from "@/hooks/useContentWorkspace";
import { Button } from "./ui/button";
import { NotificationDrawer } from "./NotificationDrawer";
import { useInAppNotifications } from "@/hooks/useInAppNotifications";
import { API } from "@/lib/api/endpoints";
import { request } from "@/lib/api/request";
import { NOTIFICATION_REFETCH_INTERVAL_MS } from "@/lib/notification-queries";
import {
    BrandResponse,
    ChatSessionResponse,
} from "@/lib/api/contracts";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "./ui/alert-dialog";

export default function Sidebar() {
    const { isSidebarOpen, toggleSidebar } = useSidebar();
    const { user, canAccessModule } = useRBAC();
    const { notifications: localNotifications } = useInAppNotifications(user?.id);
    const { data: unreadNotificationCountData } = useQuery({
        queryKey: ["notifications", user?.id, "unread-count"],
        enabled: Boolean(user?.id),
        queryFn: () => request(API.NOTIFICATIONS.UNREAD_COUNT),
        refetchOnWindowFocus: "always",
        refetchInterval: user?.id ? NOTIFICATION_REFETCH_INTERVAL_MS : false,
    });
    const { data: brands } = useBrands(user?.role !== "PLATFORM_OWNER");
    const path = usePathname();
    const router = useRouter();
    const searchParams = useSearchParams();
    const activeChatId = searchParams.get("chat") || "";

    const isWorkspacePath = path.startsWith("/brand_space/") && !path.startsWith("/brand_space/new");
    // const isProfilePath = path === "/profile";
    const currentBrandKey = isWorkspacePath ? path.split("/")[2] : undefined;
    const liveBrands = brands || [];
    const currentBrand = resolveBrandByRouteKey(liveBrands, currentBrandKey);
    const workspaceBrands = liveBrands.filter((brand) => brand.lifecycle_state !== "deleted" && brand.lifecycle_state !== "archived");

    const filteredSidebarItems = sidebarItems.filter((item) => (user ? canAccessModule(item.module) : false));
    const isPlatformOwner = user?.role === "PLATFORM_OWNER";
    const unreadNotificationCount =
        (unreadNotificationCountData?.unread_count || 0) +
        localNotifications.filter((notification) => notification.unread).length;
    const unreadNotificationLabel = unreadNotificationCount > 99 ? "99+" : String(unreadNotificationCount);

    return (
        <aside
            className={cn(
                "sticky top-2 flex shrink-0 flex-col overflow-hidden border border-[#ECEEF5] bg-sidebar-primary text-[#666666] transition-all duration-300 ease-in-out",
                // isPlatformOwner
                //     ? "h-[calc(100vh-16px)] w-64 rounded-tr-lg rounded-br-lg"
                isSidebarOpen
                    ? "h-[calc(100vh-16px)] w-64 rounded-tr-xl"
                    : "h-[calc(100vh-16px)] w-16 rounded-br-xl",
            )}
        >
            <div className={cn("flex items-center justify-between pl-3 pr-1 py-5", !isSidebarOpen && "justify-center px-3")}>
                <button className={cn("font-dmSans text-[32px] font-bold tracking-[-0.01em] text-primary", !isSidebarOpen && "hidden")}>
                    <Image src="/VIOLYT-LOGO-PurpleTM.svg" alt="Violyt" width={34} height={28} className="h-7 w-24 border-none p-0 cursor-pointer" onClick={() => router.push("/dashboard")} />
                </button>
                <abbr title={!isSidebarOpen && "Toggle Sidebar" || ""}>
                    <Button
                        variant="ghost"
                        onClick={() => toggleSidebar()}
                        className={cn(
                            "h-8 w-8 cursor-e-resize rounded-md p-0 text-primary transition hover:bg-[#ECEEF7]",
                            !isPlatformOwner && !isSidebarOpen && "cursor-pointer",
                        )}
                    >
                        <Image src="/toggleSidebar.svg" alt="toggle" width={16} height={16} className="h-4 w-4" />
                    </Button>
                </abbr>
            </div>

            <nav className={`flex min-h-0 flex-1 flex-col pb-3 ${!isSidebarOpen && "px-2"}`}>
                <div className="min-h-0 flex-1 space-y-1 overflow-hidden">
                    {filteredSidebarItems.map((item) => {
                        const iconName = item.icon.replace(/^\//, "");
                        const activeItem =
                            path === item.href ||
                            (item.href && item.href !== "/brand_space" ? path.startsWith(`${item.href}/`) : false);
                        const icon = activeItem ? `/sidebar/${iconName}-white.svg` : `/sidebar/${iconName}.svg`;
                        const isBrandSpacesItem = item.href === "/brand_space";

                        return (
                            <div key={item.id} className={`w-full ${isSidebarOpen && "pl-1.5 pr-3 py-1.5"}`}>
                                {item.href ? (
                                    <Link
                                        href={item.href}
                                        className={cn(
                                            "flex items-center gap-3 py-3 px-2 text-base transition",
                                            activeItem ? "bg-primary text-white" : "text-[#5F6372] hover:bg-[#EFF1F8]",
                                            !isSidebarOpen && "justify-center px-3",
                                        )}
                                    >
                                        <Image src={icon} width={20} height={20} alt={item.name} className="h-5 w-5" />
                                        <span className={cn("text-[16px]", isBrandSpacesItem && "min-w-0 flex-1", !isSidebarOpen && "hidden")}>{item.name}</span>
                                        {isBrandSpacesItem && isSidebarOpen && isWorkspacePath ? (
                                            <ChevronDown className="h-4 w-4 shrink-0 text-current" />
                                        ) : null}
                                    </Link>
                                ) : (
                                    <NotificationDrawer>
                                        <button
                                            className={cn(
                                                "flex w-full cursor-pointer items-center gap-3 px-2 py-3 text-left text-base text-[#5F6372] transition hover:bg-[#EFF1F8]",
                                                !isPlatformOwner && !isSidebarOpen && "justify-center px-3",
                                            )}
                                            type="button"
                                        >
                                            <span className="relative inline-flex h-5 w-5 shrink-0">
                                                <Image src={icon} width={20} height={20} alt={item.name} className="h-5 w-5" />
                                                {unreadNotificationCount > 0 ? (
                                                    <span
                                                        className="absolute -right-2 -top-2 flex h-5 min-w-5 items-center justify-center rounded-full bg-[#FF6D5E] px-1 text-[10px] font-semibold leading-none text-white shadow-sm"
                                                        aria-label={`${unreadNotificationCount} unread notifications`}
                                                    >
                                                        {unreadNotificationLabel}
                                                    </span>
                                                ) : null}
                                            </span>
                                            <span className={cn("text-[16px]", !isPlatformOwner && !isSidebarOpen && "hidden")}>{item.name}</span>
                                        </button>
                                    </NotificationDrawer>
                                )}

                                {isBrandSpacesItem && isSidebarOpen && isWorkspacePath && currentBrand ? (
                                    <div
                                        className="mt-2 min-h-0 space-y-2 overflow-y-auto pl-3 pr-1 thin-scrollbar"
                                        style={{ maxHeight: "clamp(96px, calc(100vh - 420px), 240px)" }}
                                    >
                                        {workspaceBrands.map((brand) => (
                                            <BrandChatGroup
                                                key={brand.id}
                                                brand={brand}
                                                activeChatId={activeChatId}
                                                isCurrentBrand={brand.id === currentBrand.id}
                                            />
                                        ))}
                                    </div>
                                ) : null}
                            </div>
                        );
                    })}
                </div>

                <div className="shrink-0 pt-2">
                    <Link
                        href="/profile"
                        className={cn(
                            "flex items-center gap-3 rounded-[10px] px-3 py-2 transition hover:bg-[#EFF1F8]",
                            !isSidebarOpen && "justify-center px-2",
                        )}
                    >
                        <span className={cn("flex items-center justify-center rounded-full bg-[#52B2CF] font-medium text-white", !isSidebarOpen ? "h-8 w-8 text-sm" : "h-[38px] w-[38px] text-base")}>
                            {user?.name?.[0] || "P"}
                        </span>
                        <span className={cn("text-[15px] font-medium text-[#2F3342]", !isSidebarOpen && "hidden")}>
                            {user?.name || "Indo Sakura"}
                        </span>
                    </Link>
                </div>
            </nav>
        </aside>
    );
}

const defaultStudioPanel = {
    format: "static",
    platform_preset: "instagram",
    file_type: "png",
    size: { width: 1080, height: 1080 },
};

function BrandChatGroup({
    brand,
    activeChatId,
    isCurrentBrand,
}: {
    brand: BrandResponse;
    activeChatId: string;
    isCurrentBrand: boolean;
}) {
    const router = useRouter();
    const { data: chatSessions = [] } = useChatSessions(brand.id);
    const createChatSession = useCreateChatSession(brand.id);
    const updateChatSession = useUpdateChatSession(brand.id);
    const deleteChatSession = useDeleteChatSession(brand.id);
    const [isOpen, setIsOpen] = useState(isCurrentBrand);
    const [editingSessionId, setEditingSessionId] = useState("");
    const [editingTitle, setEditingTitle] = useState("");
    const [pendingDeleteSession, setPendingDeleteSession] = useState<ChatSessionResponse | null>(null);
    const renameInFlightRef = useRef(false);
    const deleteInFlightRef = useRef(false);

    useEffect(() => {
        if (isCurrentBrand) {
            setIsOpen(true);
        }
    }, [isCurrentBrand]);

    const handleCreateChat = async () => {
        const session = await createChatSession.mutateAsync({
            title: "Untitled chat",
            studio_panel: defaultStudioPanel,
        });
        setIsOpen(true);
        router.push(buildBrandChatHref(brand, session.id));
    };

    const beginRename = (sessionId: string, title: string) => {
        setEditingSessionId(sessionId);
        setEditingTitle(title);
    };

    const submitRename = () => {
        if (renameInFlightRef.current) {
            return;
        }
        const sessionId = editingSessionId;
        const title = editingTitle.trim();
        if (!sessionId) {
            return;
        }
        setEditingSessionId("");
        setEditingTitle("");
        if (title) {
            renameInFlightRef.current = true;
            updateChatSession.mutate(
                { sessionId, data: { title } },
                {
                    onSettled: () => {
                        renameInFlightRef.current = false;
                    },
                },
            );
        }
    };

    const confirmDeleteChat = () => {
        if (deleteInFlightRef.current) {
            return;
        }
        if (!pendingDeleteSession) {
            return;
        }
        const sessionId = pendingDeleteSession.id;
        deleteInFlightRef.current = true;
        setPendingDeleteSession(null);
        if (activeChatId === sessionId) {
            const nextSession = chatSessions.find((session) => session.id !== sessionId);
            router.push(nextSession ? buildBrandChatHref(brand, nextSession.id) : buildBrandWorkspaceHref(brand));
        }
        deleteChatSession.mutate(sessionId, {
            onSettled: () => {
                deleteInFlightRef.current = false;
            },
        });
    };

    return (
        <div className="space-y-1">
            <div
                className={cn(
                    "px-3 py-3 transition",
                    isCurrentBrand ? "bg-primary text-white" : "text-[#5F6372] hover:bg-[#EFF1F8]",
                )}
            >
                <div className="flex items-center justify-between gap-2">
                    <button
                        type="button"
                        onClick={() => setIsOpen((current) => !current)}
                        className="flex min-w-0 flex-1 items-center gap-2 text-left text-base font-medium"
                        aria-expanded={isOpen}
                        aria-label={`${isOpen ? "Collapse" : "Expand"} ${brand.name} chats`}
                    >
                        <ChevronDown className={cn("h-4 w-4 shrink-0 transition-transform", !isOpen && "-rotate-90")} />
                        <FolderOpen className="h-4 w-4 shrink-0" />
                        <span className="truncate">{brand.name}</span>
                    </button>
                    <button
                        type="button"
                        onClick={() => void handleCreateChat()}
                        disabled={createChatSession.isPending}
                        className={cn(
                            "flex h-5 w-5 cursor-pointer items-center justify-center transition disabled:cursor-not-allowed disabled:opacity-60",
                            isCurrentBrand ? "text-white hover:bg-white/10" : "text-primary hover:bg-[#F4F4F4]",
                        )}
                        aria-label={`Create chat in ${brand.name}`}
                    >
                        <PlusCircle fill={isCurrentBrand ? "#FFFFFF" : "transparent"} className={cn("h-4 w-4", isCurrentBrand ? "text-primary" : "text-current")} />
                    </button>
                </div>
            </div>

            {isOpen && chatSessions.length ? (
                <div className="space-y-1">
                    {chatSessions.map((session: ChatSessionResponse) => {
                        const title = session.title?.trim() || "Untitled chat";
                        const isActiveChat = activeChatId ? activeChatId === session.id : isCurrentBrand && session.id === chatSessions[0]?.id;
                        return (
                            <div
                                key={session.id}
                                className={cn(
                                    "group flex items-center gap-1 px-3 py-2 text-sm transition",
                                    isActiveChat ? "bg-[#F4F4F4] text-[#666666]" : "text-[#666666] hover:bg-[#F4F4F4]",
                                )}
                            >
                                {editingSessionId === session.id ? (
                                    <div className="relative min-w-0 flex-1">
                                        <input
                                            value={editingTitle}
                                            onChange={(event) => setEditingTitle(event.target.value)}
                                            onKeyDown={(event) => {
                                                if (event.key === "Enter") {
                                                    event.preventDefault();
                                                    submitRename();
                                                }
                                                if (event.key === "Escape") {
                                                    setEditingSessionId("");
                                                    setEditingTitle("");
                                                }
                                            }}
                                            autoFocus
                                            className="w-full bg-white px-2 py-1 pr-8 text-sm text-[#2F3342] outline-none ring-1 ring-primary/30"
                                        />
                                        <button
                                            type="button"
                                            onClick={submitRename}
                                            className="absolute right-1 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center text-primary hover:bg-[#F4F4F4]"
                                            aria-label="Save chat name"
                                        >
                                            <Check className="h-4 w-4" />
                                        </button>
                                    </div>
                                ) : (
                                    <Link
                                        href={buildBrandChatHref(brand, session.id)}
                                        className="min-w-0 flex-1 truncate pl-3"
                                        title={title}
                                    >
                                        {title}
                                    </Link>
                                )}
                                {editingSessionId !== session.id ? (
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <button
                                                type="button"
                                                className="flex h-7 w-7 items-center justify-center text-[#8B8B94] opacity-0 transition hover:bg-white group-hover:opacity-100 data-[state=open]:opacity-100"
                                                aria-label={`Actions for ${title}`}
                                            >
                                                <MoreVertical className="h-4 w-4" />
                                            </button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end" className="w-36">
                                            <DropdownMenuItem onClick={() => beginRename(session.id, title)}>
                                                <Edit2 className="h-4 w-4" />
                                                Rename
                                            </DropdownMenuItem>
                                            <DropdownMenuItem variant="destructive" onClick={() => setPendingDeleteSession(session)}>
                                                <Trash2 className="h-4 w-4" />
                                                Delete
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                ) : null}
                            </div>
                        );
                    })}
                </div>
            ) : null}
            <AlertDialog open={Boolean(pendingDeleteSession)} onOpenChange={(open) => !open && setPendingDeleteSession(null)}>
                <AlertDialogContent className="max-w-[420px] rounded-none border-0 bg-white p-6 shadow-[0_20px_80px_-24px_rgba(15,23,42,0.35)]">
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete chat?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This will permanently delete {pendingDeleteSession?.title?.trim() || "this chat"}.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel className="rounded-none">Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={(event) => {
                                event.preventDefault();
                                confirmDeleteChat();
                            }}
                            className="rounded-none bg-[#FF6D5E] text-white hover:bg-[#FF6D5E]/90"
                            disabled={deleteChatSession.isPending}
                        >
                            {deleteChatSession.isPending ? "Deleting..." : "Delete"}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
