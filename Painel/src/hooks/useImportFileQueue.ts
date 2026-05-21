import { useCallback, useMemo, useState } from 'react';

export interface ImportFileItem {
  id: string;
  file: File;
}

interface UseImportFileQueueOptions {
  maxFiles: number;
  acceptedExtensions: string[];
  onLimitExceeded?: (details: { maxFiles: number; attemptedFiles: number; acceptedFiles: number }) => void;
}

export const formatFileSize = (size: number): string => {
  if (size >= 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(2)} MB`;
  }

  if (size >= 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${size} B`;
};

export function useImportFileQueue({
  maxFiles,
  acceptedExtensions,
  onLimitExceeded,
}: UseImportFileQueueOptions) {
  const [selectedFiles, setSelectedFiles] = useState<ImportFileItem[]>([]);

  const normalizedExtensions = useMemo(
    () => acceptedExtensions.map((extension) => extension.toLowerCase()),
    [acceptedExtensions],
  );

  const totalSize = useMemo(
    () => selectedFiles.reduce((acc, item) => acc + item.file.size, 0),
    [selectedFiles],
  );

  const addFiles = useCallback(
    (files: FileList | null) => {
      if (!files?.length) {
        return;
      }

      const acceptedFiles = Array.from(files).filter((file) => {
        const fileName = file.name.toLowerCase();
        return normalizedExtensions.some((extension) => fileName.endsWith(extension));
      });

      if (!acceptedFiles.length) {
        return;
      }

      setSelectedFiles((prev) => {
        const existingNames = new Set(prev.map((item) => item.file.name));
        const availableSlots = maxFiles - prev.length;

        const newItems = acceptedFiles
          .filter((file) => !existingNames.has(file.name))
          .slice(0, Math.max(availableSlots, 0))
          .map((file) => ({
            id: `${file.name}-${file.lastModified}`,
            file,
          }));

        if (acceptedFiles.length > newItems.length) {
          onLimitExceeded?.({
            maxFiles,
            attemptedFiles: acceptedFiles.length,
            acceptedFiles: newItems.length,
          });
        }

        return [...prev, ...newItems];
      });
    },
    [maxFiles, normalizedExtensions, onLimitExceeded],
  );

  const clearFiles = useCallback(() => {
    setSelectedFiles([]);
  }, []);

  return {
    selectedFiles,
    setSelectedFiles,
    addFiles,
    clearFiles,
    totalSize,
    formatFileSize,
  };
}
