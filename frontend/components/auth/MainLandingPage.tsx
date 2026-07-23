"use client"

import { useEffect } from "react";
import { useRBAC } from "@/hooks/useRBAC";
import Image from "next/image";
import { useRouter } from "next/navigation";

export const metadata = {
  title: "Login - Violyt",
  description: "Access your brand intelligence workspace",
};

export default function MainAuthLandingPage({ children }: { children: React.ReactNode }) {
    const { user, isPending } = useRBAC();
    const router = useRouter();

    useEffect(() => {
        if (isPending || !user) {
            return;
        }

        if (user.role === "PLATFORM_OWNER") {
            router.replace("/tenants");
            return;
        }else{
            router.replace("/brand_space");
        }
    }, [isPending, user, router]);

  return (
    <div className="min-h-screen bg-white md:grid md:grid-cols-2">
      <div className="relative hidden min-h-screen overflow-hidden md:flex md:flex-col md:justify-between">
        {/* <div className="absolute inset-0 bg-[linear-gradient(123deg,#8266BA_0%,#624CA6_38%,#3C2F8F_83%)]" /> */}
        <Image
          src="/auth_bg.svg"
          alt="Violyt Logo"
          width={200}
          height={100}
          className="absolute inset-0 h-full w-full object-cover"
        />
        {/* <div className="absolute inset-0 bg-[radial-gradient(circle_at_12%_90%,rgba(255,255,255,0.18),transparent_34%)]" /> */}

        <div className="relative px-8 py-10 lg:px-[34px] lg:py-[40px]">
            <Image src="/VIOLYT-LOGO-PurpleTM_White.svg" alt="Violyt" width={130} height={52} className="border-none p-0" />
          {/* <p className="font-dmSans text-[48px] font-bold tracking-[-0.02em] text-white">Violyt</p> */}
        </div>

        <div className="relative px-8 pb-14 lg:px-[34px] lg:pb-[94px]">
          <h1 className="max-w-[476px] font-dmSans text-[56px] font-semibold leading-[1.1]   text-white lg:text-[56px]">
            Scale Without
            <br />
            Brand Dilution.
          </h1>
          <p className="mt-5 font-manrope text-xl font-[500] text-white lg:text-[20px]">
            Intelligence That Protects Your Brand.
          </p>
        </div>
      </div>

      <div className="flex min-h-screen items-center justify-center px-6 py-12 md:px-16 lg:px-[145px]">
        {children}
      </div>
    </div>
  );
}
