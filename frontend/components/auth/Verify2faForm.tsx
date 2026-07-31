"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { REGEXP_ONLY_DIGITS } from "input-otp";
import { getTwoFactorEmail, getTwoFactorTicket } from "@/lib/api/session";
import type { CurrentUserResponse } from "@/lib/api/contracts";
import { API } from "@/lib/api/endpoints";
import { request } from "@/lib/api/request";
import { getApiErrorMessage } from "@/lib/api/error-message";
import { roleFromRoleCodes, safeAppRedirectForRole } from "@/lib/role-navigation";
import { useVerifyTwoFactor } from "@/hooks/useAuthProfile";

const LOGIN_REDIRECT_KEY = "violyt.login_redirect";
async function resolvePostLoginRedirect(requestedRedirect: string) {
  const profile = await request(API.USER.GET_ME) as CurrentUserResponse;
  return safeAppRedirectForRole(roleFromRoleCodes(profile.role_codes), requestedRedirect);
}

const Verify2faForm = () => {
  const router = useRouter();
  const verifyTwoFactor = useVerifyTwoFactor();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [isLocked, setIsLocked] = useState(false);
  const ticket = getTwoFactorTicket();
  const email = getTwoFactorEmail();

  const focusOtpInput = () => {
    window.requestAnimationFrame(() => {
      const otpElement = document.getElementById("two-factor-code");
      const focusTarget = otpElement instanceof HTMLInputElement ? otpElement : otpElement?.querySelector("input");
      focusTarget?.focus();
    });
  };

  const handleVerify = async () => {
    if (!ticket) {
      setError("Your login challenge expired. Please sign in again.");
      return;
    }
    if (code.length !== 6) {
      setError("Enter the 6 digit authenticator code.");
      return;
    }
    setError("");
    verifyTwoFactor.mutate(
      { ticket, code },
      {
        onSuccess: async () => {
          const redirectTo = window.sessionStorage.getItem(LOGIN_REDIRECT_KEY) || "/dashboard";
          window.sessionStorage.removeItem(LOGIN_REDIRECT_KEY);
          router.replace(await resolvePostLoginRedirect(redirectTo));
        },
        onError: (error) => {
          const message = getApiErrorMessage(error, "Invalid verification code. Please try again.");
          setError(message);
          const locked = message.toLowerCase().includes("temporarily locked");
          setIsLocked(locked);
          setCode("");
          if (!locked) {
            focusOtpInput();
          }
        },
      },
    );
  };

  return (
    <div className="w-full space-y-6">
      {email ? <p className="text-sm text-gray-500">Verifying access for {email}</p> : null}

      <Field className="my-4 mb-5 w-fit">
        <InputOTP value={code} onChange={setCode} id="two-factor-code" maxLength={6} pattern={REGEXP_ONLY_DIGITS} disabled={isLocked || verifyTwoFactor.isPending}>
          <InputOTPGroup className="gap-3">
            <InputOTPSlot index={0} />
            <InputOTPSlot index={1} />
            <InputOTPSlot index={2} />
            <InputOTPSlot index={3} />
            <InputOTPSlot index={4} />
            <InputOTPSlot index={5} />
          </InputOTPGroup>
        </InputOTP>
      </Field>

      {error ? <p className="text-sm text-red-500">{error}</p> : null}

      <Button
        type="button"
        onClick={handleVerify}
        disabled={isLocked || verifyTwoFactor.isPending}
        className="w-full rounded-none bg-[#5A4BB0] py-5 text-base font-semibold hover:bg-[#4A3C98]"
      >
        {verifyTwoFactor.isPending ? "Verifying..." : "Verify"}
      </Button>

      <button
        type="button"
        onClick={() => router.replace("/auth/login")}
        className="text-sm font-semibold text-[#5A4BB0]"
      >
        Back to login
      </button>

      {/* <p className="text-base text-gray-500">Secure access to your brand intelligence environment.</p> */}
    </div>
  );
};

export default Verify2faForm;

