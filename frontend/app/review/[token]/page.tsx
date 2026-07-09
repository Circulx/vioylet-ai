import ShareReviewScreen from "@/components/sharing/ShareReviewScreen";

type PublicReviewPageProps = {
  params: Promise<{ token: string }> | { token: string };
};

export default async function PublicReviewPage({
  params,
}: PublicReviewPageProps) {
  const resolvedParams = await params;
  return <ShareReviewScreen reviewToken={resolvedParams.token} externalMode />;
}
