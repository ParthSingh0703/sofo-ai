import { Search, Pencil, Trash2, Check, X, Loader2 } from 'lucide-react';
import { useState } from 'react';

interface MediaCardProps {
    image: {
        id: string;
        src: string;
        room: string;
        description: string;
        isMain: boolean;
        isProcessing?: boolean;
    };
    index: number;
    onMagnify: (index: number) => void;
    onEdit: (index: number, data: { room: string; description: string }) => void;
    onDelete: (index: number) => void;
}

const MediaCard = ({ image, index, onMagnify, onEdit, onDelete }: MediaCardProps) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editData, setEditData] = useState({
        room: image.room,
        description: image.description
    });

    const handleEditClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        setIsEditing(true);
    };

    const handleCancelClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        setIsEditing(false);
        setEditData({ room: image.room, description: image.description });
    };

    const handleSaveClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        onEdit(index, editData);
        setIsEditing(false);
    };

    const handleChange = (field: 'room' | 'description', value: string) => {
        setEditData(prev => ({ ...prev, [field]: value }));
    };

    const handleInputClick = (e: React.MouseEvent) => e.stopPropagation();

    return (
  <div
    className="
      group
      relative
      w-full
      aspect-[16/10]
      rounded-xl
      overflow-hidden
      bg-[#1a1a1a]
      border border-transparent
      transition-colors duration-200
      hover:border-(--accent-blue)
    "
  >
    {image.isMain && (
      <div
        className="
          absolute top-[10px] left-[10px]
          bg-(--accent-blue)
          text-white
          text-[0.6rem]
          font-bold
          px-2 py-1
          rounded
          uppercase
          z-2
        "
      >
        MAIN PHOTO
      </div>
    )}

    <img
      src={image.src}
      alt={image.room}
      className="w-full h-full object-cover block"
    />

    {image.isProcessing && (
      <div
        className="
          absolute inset-0
          bg-black/40
          flex items-center justify-center
          z-3
          backdrop-blur-[1px]
        "
      >
        <div className="flex flex-col items-center gap-3 text-white">
          <Loader2
            size={24}
            className="animate-[spin_1s_linear_infinite]"
          />
          <span className="text-[0.85rem] font-semibold uppercase tracking-[0.5px]">
            Processing...
          </span>
        </div>
      </div>
    )}

    {!isEditing && !image.isProcessing && (
      <div
        className="
          absolute inset-0
          bg-black/40
          opacity-0
          flex items-center justify-center
          gap-4
          transition-opacity duration-200
          group-hover:opacity-100
        "
      >
        <button
          onClick={() => onMagnify(index)}
          title="Magnify"
          className="
            w-[36px] h-[36px]
            rounded-full
            bg-white/20
            border border-white/30
            text-white
            flex items-center justify-center
            cursor-pointer
            backdrop-blur
            transition-all duration-200
            hover:bg-white hover:text-black hover:scale-110
          "
        >
          <Search size={18} />
        </button>

        <button
          onClick={handleEditClick}
          title="Edit Details"
          className="
            w-[36px] h-[36px]
            rounded-full
            bg-white/20
            border border-white/30
            text-white
            flex items-center justify-center
            cursor-pointer
            backdrop-blur
            transition-all duration-200
            hover:bg-white hover:text-black hover:scale-110
          "
        >
          <Pencil size={18} />
        </button>

        <button
          onClick={() => onDelete(index)}
          title="Delete Asset"
          className="
            w-[36px] h-[36px]
            rounded-full
            bg-white/20
            border border-white/30
            text-white
            flex items-center justify-center
            cursor-pointer
            backdrop-blur
            transition-all duration-200
            hover:bg-white hover:text-black hover:scale-110
          "
        >
          <Trash2 size={18} />
        </button>
      </div>
    )}

    {!image.isProcessing && (
      <div
        className={`
          absolute bottom-0 left-0 right-0
          p-4
          text-white
          transition-all duration-200 ease
          ${
            isEditing
              ? 'bg-black/95 h-full flex items-center justify-center'
              : 'bg-gradient-to-t from-black/90 to-transparent'
          }
        `}
      >
        {isEditing ? (
          <div className="w-full flex flex-col gap-2">
            <input
              className="
                w-full
                bg-white/10
                border border-white/20
                text-white
                p-2
                rounded
                font-inherit
                text-[0.85rem]
                focus:outline-none
                focus:border-(--accent-blue)
                focus:bg-white/15
              "
              value={editData.room}
              onChange={(e) => handleChange('room', e.target.value)}
              onClick={handleInputClick}
              placeholder="Room Type"
            />

            <textarea
              rows={2}
              className="
                w-full
                bg-white/10
                border border-white/20
                text-white
                p-2
                rounded
                font-inherit
                text-[0.75rem]
                resize-none
                focus:outline-none
                focus:border-(--accent-blue)
                focus:bg-white/15
              "
              value={editData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              onClick={handleInputClick}
              placeholder="Description"
            />

            <div className="flex gap-2 mt-2">
              <button
                onClick={handleSaveClick}
                className="
                  flex-1
                  p-[0.4rem]
                  rounded
                  text-[0.7rem]
                  font-semibold
                  flex items-center justify-center gap-1
                  uppercase
                  cursor-pointer
                  bg-(--success-green)
                  text-white
                  border-none
                "
              >
                <Check size={14} /> SAVE
              </button>

              <button
                onClick={handleCancelClick}
                className="
                  flex-1
                  p-[0.4rem]
                  rounded
                  text-[0.7rem]
                  font-semibold
                  flex items-center justify-center gap-1
                  uppercase
                  cursor-pointer
                  bg-white/10
                  text-white
                  border border-white/10
                "
              >
                <X size={14} /> CANCEL
              </button>
            </div>
          </div>
        ) : (
          <>
            {image.room && (
              <div className="text-[0.85rem] font-bold uppercase mb-[0.2rem]">
                {image.room}
              </div>
            )}
            {image.description && (
              <div className="text-[0.7rem] text-white/80 line-clamp-2">
                {image.description}
              </div>
            )}
          </>
        )}
      </div>
    )}
  </div>
);
 
};

export default MediaCard;
