import UserEditorForm from "@/components/userManagement/UserEditorForm";
import UserOverview from "@/components/userManagement/UserOverview";

type UserDetailPageProps = {
  params: Promise<{ userId: string }>;
  searchParams: Promise<{ edit?: string }>;
};

export default async function UserDetailPage({
  params,
  searchParams,
}: UserDetailPageProps) {
  const { userId } = await params;
  const resolvedSearchParams = await searchParams;

  return resolvedSearchParams.edit === "true" ? (
    <UserEditorForm mode="edit" userId={userId} />
  ) : (
    <UserOverview userId={userId} />
  );
}
