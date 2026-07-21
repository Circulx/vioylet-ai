"use client";

import { isAxiosError } from "axios";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { FormField, StyledInput } from "@/components/brandSpaces/tabs/FormFields";
import { PlatformPageTitle, SectionCard } from "@/components/platformOwner/PlatformOwnerPrimitives";
import { useBrands } from "@/hooks/useBrands";
import { getTenantUserRequestId, useSaveTenantUser, useTenantUserDetail } from "@/hooks/useTeamAccess";
import { useGetMe } from "@/hooks/useUser";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { toast } from "@/components/ui/use-toast";

type UserEditorFormProps = {
    mode: "create" | "edit";
    userId?: string;
};

type UserEditorState = {
    fullName: string;
    email: string;
    contactNumber: string;
    roleCode: "tenant_admin" | "tenant_user" | "brand_user";
    selectedBrands: string[];
};

type FormErrorState = {
    fullName?: string;
    email?: string;
    contactNumber?: string;
    selectedBrands?: string;
};

type SubmissionFeedback = {
    title: string;
    description: string;
};

function isSupportedRoleSwap(oldRoleCode: UserEditorState["roleCode"], newRoleCode: UserEditorState["roleCode"]) {
    return (
        oldRoleCode !== newRoleCode &&
        [oldRoleCode, newRoleCode].every((roleCode) => roleCode === "tenant_user" || roleCode === "brand_user")
    );
}

function getMutationErrorMessage(error: unknown, mode: UserEditorFormProps["mode"]) {
    if (isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim()) {
            return detail;
        }
    }
    return mode === "create"
        ? "We could not create the user right now."
        : "We could not save the changes right now.";
}

export default function UserEditorForm({ mode, userId }: UserEditorFormProps) {
    const router = useRouter();
    const { data: brands } = useBrands();
    const { data: currentUser } = useGetMe();
    const { data: liveUser, isLoading } = useTenantUserDetail(userId || "");
    const saveUserId = mode === "edit" ? getTenantUserRequestId(liveUser) || userId : undefined;

    const saveUser = useSaveTenantUser(saveUserId);
    const [confirmOpen, setConfirmOpen] = useState(false);
    const [errors, setErrors] = useState<FormErrorState>({});
    const [submissionFeedback, setSubmissionFeedback] = useState<SubmissionFeedback | null>(null);

    const [form, setForm] = useState<UserEditorState | null>(null);
    const initialForm = useMemo<UserEditorState>(() => {
        if (liveUser) {
            return {
                fullName: liveUser.full_name,
                email: liveUser.email,
                contactNumber: liveUser.phone_number || "",
                roleCode: liveUser.role_codes.includes("tenant_admin")
                    ? "tenant_admin"
                    : liveUser.role_codes.includes("tenant_user")
                        ? "tenant_user"
                        : "brand_user",
                selectedBrands: liveUser.brand_space_ids,
            };
        }
        return {
            fullName: "",
            email: "",
            contactNumber: "",
            roleCode: "tenant_user",
            selectedBrands: [],
        };
    }, [liveUser]);
    const resolvedForm = form ?? initialForm;

    const availableBrands = useMemo(
        () =>
            (brands || []).filter((brand) => brand.lifecycle_state !== "deleted").map((brand) => ({
                id: brand.id,
                name: brand.name,
            })),
        [brands],
    );

    const roleLabel =
        resolvedForm.roleCode === "tenant_admin"
            ? "Tenant Admin"
            : resolvedForm.roleCode === "tenant_user"
                ? "Super User"
                : "Brand User";
    const title =
        mode === "create"
            ? "Create User"
            : `Edit ${resolvedForm.fullName || (resolvedForm.roleCode === "brand_user" ? "{Brand user name}" : "{Super User name}")}`;

    const showBrandAssignment = resolvedForm.roleCode === "brand_user";
    const liveUserId = getTenantUserRequestId(liveUser);
    const isSelfEdit = mode === "edit" && Boolean(currentUser?.id) && liveUserId === currentUser?.id;

    const updateForm = (patch: Partial<UserEditorState>) => {
        setForm((current) => ({ ...(current ?? resolvedForm), ...patch }));
    };

    const toggleBrand = (brandId: string) => {
        setErrors((current) => ({ ...current, selectedBrands: undefined }));
        updateForm({
            selectedBrands: resolvedForm.selectedBrands.includes(brandId)
                ? resolvedForm.selectedBrands.filter((item) => item !== brandId)
                : [...resolvedForm.selectedBrands, brandId],
        });
    };

    const validate = () => {
        const nextErrors: FormErrorState = {};
        if (!resolvedForm.fullName.trim()) {
            nextErrors.fullName = "Full name is required.";
        }
        if (!resolvedForm.email.trim()) {
            nextErrors.email = "Email address is required.";
        }
        if (!resolvedForm.contactNumber.trim()) {
            nextErrors.contactNumber = "Contact number is required.";
        }
        if (showBrandAssignment && resolvedForm.selectedBrands.length === 0) {
            nextErrors.selectedBrands = "Assign at least one brand space for a brand user.";
        }
        setErrors(nextErrors);
        return Object.keys(nextErrors).length === 0;
    };

    const submit = () => {
        if (saveUser.isPending) {
            return;
        }
        const roleChangedByTenantAdmin =
            mode === "edit" &&
            currentUser?.role === "TENANT_ADMIN" &&
            isSupportedRoleSwap(initialForm.roleCode, resolvedForm.roleCode);
        setSubmissionFeedback(null);
        saveUser.mutate(
            {
                full_name: resolvedForm.fullName,
                email: resolvedForm.email,
                phone_number: resolvedForm.contactNumber,
                role_code: resolvedForm.roleCode,
                brand_space_ids: showBrandAssignment ? resolvedForm.selectedBrands : [],
            },
            {
                onSuccess: (savedUser) => {
                    setConfirmOpen(false);
                    if (mode === "create") {
                        const params = new URLSearchParams({
                            created: "1",
                            email: savedUser.activation_email?.recipient_email || savedUser.email,
                            emailStatus: savedUser.activation_email?.delivered
                                ? "sent"
                                : savedUser.activation_email?.attempted
                                    ? "failed"
                                    : "skipped",
                        });
                        if (savedUser.activation_email?.reason) {
                            params.set("emailReason", savedUser.activation_email.reason);
                        }
                        router.push(`/user_management?${params.toString()}`);
                        return;
                    }
                    if (roleChangedByTenantAdmin) {
                        toast({
                            title: "User role updated successfully.",
                            variant: "success",
                        });
                        router.push(`/user_management/${getTenantUserRequestId(savedUser)}`);
                        return;
                    }
                    const shouldShowProfileUpdateToast =
                        (currentUser?.role === "PLATFORM_OWNER" && savedUser.role_codes.includes("tenant_admin")) ||
                        (currentUser?.role === "TENANT_ADMIN" &&
                            (savedUser.role_codes.includes("tenant_user") || savedUser.role_codes.includes("brand_user")));
                    if (shouldShowProfileUpdateToast) {
                        toast({
                            title: "Your profile has been updated successfully.",
                            variant: "success",
                        });
                    }
                    router.push(`/user_management/${getTenantUserRequestId(savedUser)}`);
                },
                onError: (error) => {
                    setSubmissionFeedback({
                        title: mode === "create" ? "User creation failed" : "Could not save changes",
                        description: getMutationErrorMessage(error, mode),
                    });
                },
            },
        );
    };

    const handleSaveClick = () => {
        if (!validate()) {
            return;
        }
        if (mode === "edit") {
            setConfirmOpen(true);
            return;
        }
        submit();
    };

    if (mode === "edit" && isLoading && !liveUser) {
        return <div className="w-full px-6 py-10 text-sm text-slate-500">Loading user details...</div>;
    }

    if (mode === "edit" && !isLoading && !liveUser) {
        return <div className="w-full px-6 py-10 text-sm text-slate-500">User not found.</div>;
    }

    return (
        <>
            <div className="w-full px-4 py-6">
                <div className="mx-auto ">
                    <PlatformPageTitle
                        title={title}
                        action={
                            <Button
                                onClick={handleSaveClick}
                                disabled={saveUser.isPending}
                                className="h-12 rounded-none bg-primary/72 px-10 py-6 text-[15px] font-medium hover:bg-primary/90"
                            >
                                {saveUser.isPending ? (mode === "create" ? "Creating..." : "Saving...") : mode === "create" ? "Create" : "Save"}
                            </Button>
                        }
                    />

                    {submissionFeedback ? (
                        <Alert variant="destructive">
                            <AlertTitle>{submissionFeedback.title}</AlertTitle>
                            <AlertDescription>{submissionFeedback.description}</AlertDescription>
                        </Alert>
                    ) : null}

                    <SectionCard className="border-none shadow-none p-0">
                        <div className="max-w-md space-y-6">
                            <FormField label="Full Name" required error={errors.fullName}>
                                <StyledInput
                                    placeholder="Enter full name"
                                    value={resolvedForm.fullName}
                                    onChange={(event) => {
                                        setErrors((current) => ({ ...current, fullName: undefined }));
                                        updateForm({ fullName: event.target.value });
                                    }}
                                />
                            </FormField>

                            <FormField label="Email Address" required error={errors.email}>
                                <StyledInput
                                    placeholder="Enter email address"
                                    value={resolvedForm.email}
                                    onChange={(event) => {
                                        setErrors((current) => ({ ...current, email: undefined }));
                                        updateForm({ email: event.target.value });
                                    }}
                                />
                            </FormField>

                            <FormField label="Contact Number" required error={errors.contactNumber}>
                                <StyledInput
                                    placeholder="Enter contact number"
                                    value={resolvedForm.contactNumber}
                                    onChange={(event) => {
                                        setErrors((current) => ({ ...current, contactNumber: undefined }));
                                        updateForm({ contactNumber: event.target.value });
                                    }}
                                />
                            </FormField>

                            <FormField label="User Role" required>
                                <Select
                                    // className="h-12 w-full rounded-[10px] border-none bg-input-field px-4 text-sm text-slate-700 outline-none"
                                    value={resolvedForm.roleCode}
                                    disabled={isSelfEdit}
                                    onValueChange={(event) => {
                                        if (isSelfEdit) {
                                            return;
                                        }
                                        const nextRole = event as UserEditorState["roleCode"];
                                        updateForm({
                                            roleCode: nextRole,
                                            selectedBrands: nextRole === "brand_user" ? resolvedForm.selectedBrands : [],
                                        });
                                    }}
                                >
                                    <SelectTrigger className="w-full bg-[#F5F7FA] rounded-[10px] border-none px-4 py-6 text-sm text-slate-700 cursor-pointer">
                                        <SelectValue placeholder="Select a fruit" />
                                    </SelectTrigger>

                                    <SelectContent>
                                        <SelectGroup>
                                            {mode === "edit" && resolvedForm.roleCode === "tenant_admin" ? (
                                                <SelectItem value="tenant_admin">Tenant Admin</SelectItem>
                                            ) : null}
                                            <SelectItem value="tenant_user">Super User</SelectItem>
                                            <SelectItem value="brand_user">Brand User</SelectItem>
                                        </SelectGroup>
                                    </SelectContent>
                                </Select>
                            </FormField>

                            {showBrandAssignment ? (
                                <div className="space-y-3">
                                    <p className="text-base font-medium text-slate-700">
                                        Brand Assignment <span className="text-red-500">*</span>
                                    </p>
                                    <div className="overflow-hidden rounded-xs bg-white">
                                        <div className="rounded-md bg-[#F5F6FB] px-4 py-3 text-sm text-[#6B7280]">
                                            Assign brand space
                                        </div>
                                        <div className="divide-y divide-slate-100">
                                            {availableBrands.map((brand) => (
                                                <label key={brand.id} className="flex items-center gap-3 px-4 py-3 text-sm text-slate-700">
                                                    <Checkbox checked={resolvedForm.selectedBrands.includes(brand.id)} onCheckedChange={() => toggleBrand(brand.id)} />
                                                    <span>{brand.name}</span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                    {errors.selectedBrands ? <p className="text-sm text-red-500">{errors.selectedBrands}</p> : null}
                                </div>
                            ) : null}

                            {mode === "edit" ? (
                                <p className="text-sm text-slate-500">
                                    Editing <span className="font-medium text-slate-700">{roleLabel}</span> access and details.
                                </p>
                            ) : null}
                        </div>
                    </SectionCard>
                </div>
            </div>

            <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
                <AlertDialogContent className="w-[432px] max-w-[calc(100vw-32px)] gap-0 rounded-[4px] border-0 bg-white px-0 pb-[60px] pt-[60px] shadow-none">
                    <AlertDialogCancel className="absolute right-4 top-3 flex h-6 w-6 items-center justify-center rounded-full border-0 bg-[#F5F2F2] p-0 text-sm leading-none text-black hover:bg-[#F5F2F2] focus-visible:outline-none focus-visible:ring-0">
                        ×
                    </AlertDialogCancel>
                    <AlertDialogHeader className="flex items-center justify-center gap-1 text-center">
                        <AlertDialogTitle className="text-[30px] font-semibold leading-9 tracking-normal text-black">Save Changes?</AlertDialogTitle>
                        <AlertDialogDescription className="whitespace-nowrap text-[18px] leading-6 text-black">
                            Are you sure you want to save these changes?
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter className="mx-auto mt-[25px] flex w-[306px] !flex-row items-center justify-center gap-[26px]">
                        <AlertDialogAction
                            className="h-11 w-[140px] rounded-none bg-primary/72 p-0 text-base text-white hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-0"
                            onClick={submit}
                        >
                            Confirm
                        </AlertDialogAction>
                        <AlertDialogCancel className="h-11 w-[140px] rounded-none border border-black bg-white p-0 text-base text-black hover:bg-white focus-visible:outline-none focus-visible:ring-0">
                            Cancel
                        </AlertDialogCancel>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </>
    );
}
