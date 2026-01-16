import { Search, Pencil, Trash2, Check, X } from 'lucide-react';
import { useState } from 'react';
import styles from './MediaCard.module.css';

interface MediaCardProps {
    image: {
        id: string;
        src: string;
        room: string;
        description: string;
        isMain: boolean;
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
        <div className={styles.card}>
            {image.isMain && <div className={styles.badge}>MAIN PHOTO</div>}
            
            <img src={image.src} alt={image.room} className={styles.image} />

            {!isEditing && (
                <div className={styles.overlay}>
                    <button className={styles.actionButton} onClick={() => onMagnify(index)} title="Magnify">
                        <Search size={18} />
                    </button>
                    <button className={styles.actionButton} onClick={handleEditClick} title="Edit Details">
                        <Pencil size={18} />
                    </button>
                    <button className={styles.actionButton} onClick={() => onDelete(index)} title="Delete Asset">
                        <Trash2 size={18} />
                    </button>
                </div>
            )}

            <div className={`${styles.infoArea} ${isEditing ? styles.editingArea : ''}`}>
                {isEditing ? (
                    <div className={styles.editForm}>
                        <input
                            className={styles.editInput}
                            value={editData.room}
                            onChange={(e) => handleChange('room', e.target.value)}
                            onClick={handleInputClick}
                            placeholder="Room Type"
                        />
                        <textarea
                            className={styles.editTextarea}
                            value={editData.description}
                            onChange={(e) => handleChange('description', e.target.value)}
                            onClick={handleInputClick}
                            placeholder="Description"
                            rows={2}
                        />
                        <div className={styles.editActions}>
                            <button className={styles.saveButton} onClick={handleSaveClick}>
                                <Check size={14} /> SAVE
                            </button>
                            <button className={styles.cancelButton} onClick={handleCancelClick}>
                                <X size={14} /> CANCEL
                            </button>
                        </div>
                    </div>
                ) : (
                    <>
                        <div className={styles.roomType}>{image.room}</div>
                        <div className={styles.description}>{image.description}</div>
                    </>
                )}
            </div>
        </div>
    );
};

export default MediaCard;
