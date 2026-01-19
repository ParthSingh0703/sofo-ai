import {
  FileText,
  Image,
  Map,
  ShieldCheck,
  ClipboardList,
  StickyNote,
} from "lucide-react";

interface RecommendedItem {
  icon: typeof FileText;
  label: string;
  color: string;
}

const RecommendedList = () => {
  const items: RecommendedItem[] = [
    { icon: FileText, label: "Listing Agreements", color: "#60a5fa" },
    { icon: ShieldCheck, label: "Seller's Disclosure", color: "#facc15" },
    { icon: ClipboardList, label: "Tax Records", color: "#4ade80" },
    { icon: Map, label: "Floor Plans & Surveys", color: "#fb923c" },
    { icon: StickyNote, label: "Property Information Notes", color: "#a78bfa" },
    { icon: Image, label: "Property Photos", color: "#f472b6" },
  ];

  return (
    <div
      className="
      grid
      grid-cols-2
      gap-y-[0.6rem] gap-x-[1.4rem]
      w-full
      max-w-[420px]
      max-[600px]:grid-cols-1
      max-[600px]:gap-y-[0.8rem]
    "
    >
      {items.map((item, index) => {
        const Icon = item.icon;
        return (
          <div key={index} className="flex items-center gap-[0.35rem]">
            <Icon size={12} color={item.color} className="shrink-0" />
            <span className="text-[0.8rem] text-(--text-primary) whitespace-nowrap">
              {item.label}
            </span>
          </div>
        );
      })}
    </div>
  );
};

export default RecommendedList;
