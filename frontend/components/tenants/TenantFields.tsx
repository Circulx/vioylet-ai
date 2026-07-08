"use client";

import { useMemo } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { getCountryOptions, getStateOptions, type SelectOption } from "@/lib/geo-options";
import type { TenantFormData } from "@/types/tenant.types";
import type { FormErrors } from "@/zod/tenantManagement";
import TenantLogoUpload from "./LogoUpload";

interface TenantFieldsProps {
    form: TenantFormData["tenant"];
    setForm: (tenant: TenantFormData["tenant"]) => void;
    errors: FormErrors["tenant"];
    clearError: (field: string) => void;
}

export default function TenantFields({ form, setForm, errors, clearError }: TenantFieldsProps) {
    const countryOptions = useMemo(() => getCountryOptions(form.country), [form.country]);
    const stateOptions = useMemo(() => getStateOptions(form.country, form.state), [form.country, form.state]);

    return (
        <div className="w-full max-w-[1110px]">
            <div className="space-y-7">
                <div className="grid gap-8 items-start">
                    <div className="w-full flex gap-12">
                        <div className="max-w-md flex-1 space-y-6">
                            <Field
                                id="tenant-name"
                                label="Tenant Name"
                                value={form.name}
                                placeholder="Enter name"
                                error={errors?.name}
                                onChange={(value) => {
                                    setForm({ ...form, name: value });
                                    clearError("name");
                                }}
                            />

                            <Field
                                id="tenant-email"
                                label="Tenant Contact Email"
                                value={form.email}
                                placeholder="Enter email address"
                                error={errors?.email}
                                onChange={(value) => {
                                    setForm({ ...form, email: value });
                                    clearError("email");
                                }}
                            />

                            <Field
                                id="tenant-phone"
                                label="Tenant Contact Number"
                                value={form.phone}
                                placeholder="Enter contact number"
                                error={errors?.phone}
                                onChange={(value) => {
                                    setForm({ ...form, phone: value });
                                    clearError("phone");
                                }}
                            />
                        </div>
                        <TenantLogoUpload value={form.logo} onChange={(logo) => setForm({ ...form, logo })} />

                    </div>
                    <div className="max-w-md space-y-5">
                        <h2 className="text-lg font-medium leading-[26px] text-[#2F3342]">Tenant Address</h2>

                        <Field
                            id="address-1"
                            label="Address 1"
                            value={form.address1}
                            placeholder="Enter address line 1"
                            error={errors?.address1}
                            onChange={(value) => {
                                setForm({ ...form, address1: value });
                                clearError("address1");
                            }}
                        />

                        <Field
                            id="address-2"
                            label="Address 2"
                            value={form.address2 || ""}
                            placeholder="Enter address line 2"
                            onChange={(value) => setForm({ ...form, address2: value })}
                        />

                        <div className="grid gap-6 sm:grid-cols-[217px_209px]">
                            <Field
                                id="city"
                                label="City"
                                value={form.city}
                                placeholder="Enter city"
                                error={errors?.city}
                                onChange={(value) => {
                                    setForm({ ...form, city: value });
                                    clearError("city");
                                }}
                            />
                            <SelectField
                                id="country"
                                label="Country"
                                value={form.country}
                                placeholder="Select country"
                                options={countryOptions}
                                error={errors?.country}
                                onChange={(value) => {
                                    setForm({ ...form, country: value, state: "" });
                                    clearError("country");
                                    clearError("state");
                                }}
                            />
                        </div>

                        <div className="grid gap-6 sm:grid-cols-[217px_209px]">
                            <SelectField
                                id="state"
                                label="State"
                                value={form.state}
                                placeholder={form.country ? "Select state" : "Select country first"}
                                options={stateOptions}
                                error={errors?.state}
                                disabled={!form.country}
                                onChange={(value) => {
                                    setForm({ ...form, state: value });
                                    clearError("state");
                                }}
                            />
                            <Field
                                id="zip"
                                label="ZIP"
                                value={form.zip}
                                placeholder="Enter ZIP code"
                                error={errors?.zip}
                                onChange={(value) => {
                                    setForm({ ...form, zip: value });
                                    clearError("zip");
                                }}
                            />
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}

function Field({
    id,
    label,
    value,
    placeholder,
    error,
    onChange,
}: {
    id: string;
    label: string;
    value: string;
    placeholder: string;
    error?: string;
    onChange: (value: string) => void;
}) {
    return (
        <div className="space-y-2.5">
            <Label htmlFor={id} className="text-base font-medium leading-6 text-[#2F3342]">
                {label}
            </Label>
            <div className="relative">
                <Input
                    id={id}
                    value={value}
                    placeholder={placeholder}
                    className="h-12 rounded-[10px] border-none bg-input-field px-4 text-sm text-[#2F3342] placeholder:text-[#A7A7A7] focus-visible:ring-2 focus-visible:ring-primary/20"
                    onChange={(event) => onChange(event.target.value)}
                />
            </div>
            {error ? <p className="text-sm text-red-500">{error}</p> : null}
        </div>
    );
}

function SelectField({
    id,
    label,
    value,
    placeholder,
    options,
    error,
    disabled = false,
    onChange,
}: {
    id: string;
    label: string;
    value: string;
    placeholder: string;
    options: SelectOption[];
    error?: string;
    disabled?: boolean;
    onChange: (value: string) => void;
}) {
    return (
        <div className="space-y-2.5">
            <Label htmlFor={id} className="text-base font-medium leading-6 text-[#2F3342]">
                {label}
            </Label>
            <Select value={value} onValueChange={onChange} disabled={disabled}>
                <SelectTrigger
                    id={id}
                    className="h-12 w-full rounded-[10px] border-none bg-input-field px-4 text-sm text-[#2F3342] shadow-none focus-visible:ring-2 focus-visible:ring-primary/20 disabled:opacity-60"
                >
                    <SelectValue placeholder={placeholder} />
                </SelectTrigger>
                <SelectContent className="z-[80] max-h-72">
                    {options.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                            {option.label}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
            {error ? <p className="text-sm text-red-500">{error}</p> : null}
        </div>
    );
}
