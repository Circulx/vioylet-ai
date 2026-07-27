export type TenantDashboardFaq = {
  id: string;
  question: string;
  answer: string;
};

export const tenantDashboardFaqs: TenantDashboardFaq[] = [
  {
    id: "usage-capacity",
    question: "How is total capacity calculated?",
    answer:
      "Total capacity combines the selected month's content, visuals, and OCR usage against the limits assigned to your tenant.",
  },
  {
    id: "monthly-filter",
    question: "Can I view usage for a different month?",
    answer:
      "Yes. Use the month selector in Monthly Usage to switch between available reporting months and review historic usage.",
  },
  {
    id: "brand-spaces",
    question: "What does Brand Space usage show?",
    answer:
      "Brand Space usage shows how many brand spaces are currently allocated compared with the tenant limit set by the platform owner.",
  },
  {
    id: "user-count",
    question: "What does Users usage include?",
    answer:
      "Users usage counts active users assigned under your tenant, including tenant admins, super users, and brand users.",
  },
  {
    id: "limit-reached",
    question: "What should I do if a limit is reached?",
    answer:
      "Review inactive users or unused brand spaces first. If your team still needs more capacity, contact the platform owner to increase the allocation.",
  },
  {
    id: "data-refresh",
    question: "When does dashboard data refresh?",
    answer:
      "Dashboard metrics refresh when the page reloads or when new usage activity is synced by the backend services.",
  },
];
