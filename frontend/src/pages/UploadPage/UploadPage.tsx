import { useState, useCallback, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import UploadWidget from "./components/UploadWidget/UploadWidget";
import UploadedFileList from "./components/UploadedFileList/UploadedFileList";
import ActionButton from "./components/ActionButton/ActionButton";

interface FileItem {
  id: string | number;
  name: string;
  size: string;
  status: "success" | "error" | "uploading";
  documentId?: string;
  imageId?: string;
  isImage?: boolean;
}
import { apiClient } from "../../lib/api-client";
import { useAppDispatch } from "../../store/hooks";
import { setCurrentListing } from "../../store/slices/listingsSlice";
import { addToast } from "../../store/slices/uiSlice";

export default function UploadPage() {
  const { listingId } = useParams<{ listingId: string }>();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const [files, setFiles] = useState<FileItem[]>([]);
  const [isStarting, setIsStarting] = useState(false);
  const uploadingFilesRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!listingId) {
      navigate("/", { replace: true });
    } else {
      dispatch(setCurrentListing(listingId));
    }
  }, [listingId, navigate, dispatch]);

  const fileKey = (file: File) =>
    `${file.name}-${file.size}-${file.lastModified}`;

  const handleFilesSelected = useCallback(
    (newFiles: File[]) => {
      if (!listingId || newFiles.length === 0) return;

      const validFiles: File[] = [];
      const invalidFiles: string[] = [];

      newFiles.forEach((file) => {
        const ext = file.name.split(".").pop()?.toLowerCase();
        const validExts = ["pdf", "txt", "docx", "jpg", "jpeg", "png"];

        if (!ext || !validExts.includes(ext)) {
          invalidFiles.push(`${file.name} - Invalid file type`);
          return;
        }

        if (file.size > 10 * 1024 * 1024) {
          invalidFiles.push(`${file.name} - File too large (max 10MB)`);
          return;
        }

        validFiles.push(file);
      });

      if (invalidFiles.length > 0) {
        invalidFiles.forEach((msg) => {
          dispatch(addToast({ message: msg, type: "error" }));
        });
      }

      if (validFiles.length === 0) return;

      // Filter out files that are already uploaded or currently uploading
      setFiles((prev) => {
        const newValidFiles = validFiles.filter((file) => {
          const key = fileKey(file);
          const inState = prev.some((f) => f.id === key);
          const uploading = uploadingFilesRef.current.has(key);
          return !inState && !uploading;
        });

        if (newValidFiles.length === 0) return prev;

        const newFileItems: FileItem[] = newValidFiles.map((file) => {
          const ext = file.name.split(".").pop()?.toLowerCase();
          const isImage = ext ? ["jpg", "jpeg", "png"].includes(ext) : false;
          return {
            id: fileKey(file),
            name: file.name,
            size: (file.size / 1024).toFixed(2) + "kb",
            status: "uploading",
            isImage: isImage,
          };
        });

        // Start uploads
        newValidFiles.forEach(async (file) => {
          const key = fileKey(file);
          uploadingFilesRef.current.add(key);

          try {
            // Determine if file is an image or document
            const ext = file.name.split(".").pop()?.toLowerCase();
            const isImage = ext && ["jpg", "jpeg", "png"].includes(ext);
            const endpoint = isImage
              ? `/images/listings/${listingId}`
              : `/documents/listings/${listingId}`;

            const result = await apiClient.upload<{
              document_id?: string;
              image_id?: string;
            }>(endpoint, file, () => {
              // Progress callback - can be used for progress bar in future
            });

            setFiles((current) => {
              const updated = [...current];
              const foundIndex = updated.findIndex((f) => f.id === key);
              if (foundIndex >= 0) {
                updated[foundIndex] = {
                  ...updated[foundIndex],
                  status: "success",
                  documentId: result.document_id,
                  imageId: result.image_id,
                };
              }
              return updated;
            });

            uploadingFilesRef.current.delete(key);

            dispatch(
              addToast({
                message: `Successfully uploaded ${file.name}`,
                type: "success",
              }),
            );
          } catch {
            setFiles((current) => {
              const updated = [...current];
              const foundIndex = updated.findIndex((f) => f.id === key);
              if (foundIndex >= 0) {
                updated[foundIndex] = {
                  ...updated[foundIndex],
                  status: "error",
                };
              }
              return updated;
            });

            uploadingFilesRef.current.delete(key);

            dispatch(
              addToast({
                message: `Failed to upload ${file.name}`,
                type: "error",
              }),
            );
          }
        });

        return [...prev, ...newFileItems];
      });
    },
    [listingId, dispatch],
  );

  const handleStartAIEngine = useCallback(async () => {
    if (!listingId || files.length === 0) {
      return;
    }

    // Check if all files are uploaded successfully
    const hasUploading = files.some((f) => f.status === "uploading");
    const hasSuccess = files.some((f) => f.status === "success");

    if (hasUploading) {
      dispatch(
        addToast({
          message: "Please wait for all files to finish uploading",
          type: "warning",
        }),
      );
      return;
    }

    if (!hasSuccess) {
      dispatch(
        addToast({
          message: "Please upload at least one file before starting",
          type: "error",
        }),
      );
      return;
    }

    setIsStarting(true);

    try {
      // Start extraction (fire and continue - extraction may take a while)
      const extractionPromise = apiClient
        .post(`/extraction/listings/${listingId}/extract`)
        .then(() => {
          console.log("Extraction started successfully");
        })
        .catch((error) => {
          console.warn(
            "Extraction error:",
            error instanceof Error ? error.message : "Unknown error",
          );
        });

      // Start enrichment (will wait for extraction data or fail gracefully)
      // Enrichment can run independently and will check for canonical data
      const enrichmentPromise = apiClient
        .post(
          `/enrichment/listings/${listingId}/enrich?analyze_images=true&generate_descriptions=true&enrich_geo=true`,
        )
        .then(() => {
          console.log("Enrichment started successfully");
        })
        .catch((error) => {
          console.warn(
            "Enrichment error (may need extraction to complete first):",
            error instanceof Error ? error.message : "Unknown error",
          );
        });

      // Fire both processes - they will run in background
      // Processing page will handle waiting for both to complete
      Promise.allSettled([extractionPromise, enrichmentPromise]).then(() => {
        console.log("Both extraction and enrichment processes initiated");
      });

      // Navigate immediately - extraction and enrichment will continue in background
      navigate(`/processing/${listingId}`, { replace: true });
    } catch (error) {
      console.error("Error starting AI engine:", error);
      dispatch(
        addToast({
          message: "Failed to start AI engine. Please try again.",
          type: "error",
        }),
      );
      setIsStarting(false);
    }
  }, [listingId, files, navigate, dispatch]);

  const handleDeleteFile = useCallback(
    async (fileItem: FileItem) => {
      if (!listingId) return;

      // Don't allow deletion of files that are currently uploading
      if (fileItem.status === "uploading") {
        dispatch(
          addToast({
            message: "Cannot delete file while it is uploading",
            type: "warning",
          }),
        );
        return;
      }

      // Only delete from backend if file was successfully uploaded (has documentId or imageId)
      if (
        fileItem.status === "success" &&
        (fileItem.documentId || fileItem.imageId)
      ) {
        try {
          const endpoint = fileItem.isImage
            ? `/images/listings/${listingId}/${fileItem.imageId}`
            : `/documents/listings/${listingId}/${fileItem.documentId}`;

          await apiClient.delete(endpoint);

          dispatch(
            addToast({
              message: `Successfully deleted ${fileItem.name}`,
              type: "success",
            }),
          );
        } catch (error) {
          console.error("Failed to delete file from backend:", error);
          dispatch(
            addToast({
              message: `Failed to delete ${fileItem.name} from server`,
              type: "error",
            }),
          );
          // Still remove from UI even if backend deletion fails
        }
      }

      // Remove from UI state
      setFiles((prev) => prev.filter((f) => f.id !== fileItem.id));
    },
    [listingId, dispatch],
  );

  const hasSuccessfulUploads = files.some((f) => f.status === "success");
  const canStartEngine =
    hasSuccessfulUploads && !files.some((f) => f.status === "uploading");

  return (
    <div
      className="
      min-h-screen
      w-full
      flex
      items-center
      justify-center
    "
    >
      <div
        className="
        w-full
        max-w-[560px]
        flex
        flex-col
        items-center
        justify-center
        p-[1.4rem]
        animate-[fadeIn_0.5s_ease-out]
      "
      >
        <h1
          className="
          text-[2.1rem]
          font-bold
          mb-[1.4rem]
          text-(--text-primary)
          text-center
        "
        >
          Upload documents
        </h1>

        <div className="w-full flex flex-col gap-4">
          <UploadWidget onFilesSelected={handleFilesSelected} />

          {files.length > 0 && (
            <div className="w-full px-4">
              <UploadedFileList files={files} onDelete={handleDeleteFile} />
            </div>
          )}

          <div className="w-full flex justify-center">
            <ActionButton
              isActive={canStartEngine}
              onClick={handleStartAIEngine}
              isLoading={isStarting}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
