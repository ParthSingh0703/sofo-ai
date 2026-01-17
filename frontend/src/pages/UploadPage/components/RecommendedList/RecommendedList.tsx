import { FileText, Image, Map, ShieldCheck, ClipboardList, StickyNote } from 'lucide-react';
import styles from './RecommendedList.module.css';

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
    { icon: Image, label: "Property Photos", color: "#f472b6" }
  ];

  return (
    <div className={styles.grid}>
      {items.map((item, index) => {
        const Icon = item.icon;
        return (
          <div key={index} className={styles.item}>
            <Icon size={12} color={item.color} className={styles.icon} />
            <span className={styles.label}>{item.label}</span>
          </div>
        );
      })}
    </div>
  );
};

export default RecommendedList;
