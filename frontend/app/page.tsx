"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getAuth } from "@/lib/auth";

export default function Root() {
  const router = useRouter();

  useEffect(() => {
    const auth = getAuth();
    if (!auth) {
      router.replace("/login");
    } else if (auth.role === "consultant") {
      router.replace("/dashboard");
    } else {
      router.replace("/client/onboarding");
    }
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-navy-900">
      <div className="text-white text-lg animate-pulse">Loading...</div>
    </div>
  );
}
