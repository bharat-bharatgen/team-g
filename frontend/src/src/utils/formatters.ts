/**
 * Parse API datetime: backend sends naive UTC (no Z), so treat as UTC for correct IST conversion.
 */
function parseAsUTC(date: string | Date): Date {
  if (typeof date !== 'string') return date;
  const s = date.trim();
  if (!s) return new Date(NaN);
  if (s.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(s)) return new Date(s);
  return new Date(s + 'Z');
}

/**
 * Format date to Indian standard (DD/MM/YYYY) in IST
 */
export const formatDate = (date: string | Date): string => {
  try {
    const dateObj = parseAsUTC(date);
    return dateObj.toLocaleDateString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch (error) {
    return 'Invalid date';
  }
};

/**
 * Format date with time in IST (DD/MM/YYYY HH:mm IST)
 */
export const formatDateTime = (date: string | Date): string => {
  try {
    const dateObj = parseAsUTC(date);
    const formatted = dateObj.toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
    return formatted + ' IST';
  } catch (error) {
    return 'Invalid date';
  }
};

/**
 * Format time only in IST (HH:mm:ss IST)
 */
export const formatTime = (date: string | Date): string => {
  try {
    const dateObj = parseAsUTC(date);
    const formatted = dateObj.toLocaleTimeString('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
    return formatted + ' IST';
  } catch (error) {
    return 'Invalid time';
  }
};

/**
 * Format phone number for display (XXXXX XXXXX)
 */
export const formatPhoneNumber = (phone: string): string => {
  if (phone.length === 10) {
    return `${phone.slice(0, 5)} ${phone.slice(5)}`;
  }
  return phone;
};

/**
 * Format file size
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

/**
 * Get file extension from filename
 */
export const getFileExtension = (filename: string): string => {
  return filename.slice(((filename.lastIndexOf('.') - 1) >>> 0) + 2);
};

/**
 * Check if file is PDF
 */
export const isPDF = (contentType: string | undefined): boolean => {
  if (!contentType) return false;
  return contentType === 'application/pdf';
};

/**
 * Check if URL points to a PDF (by path, before query string).
 * Used when content_type is not available (e.g. face match / location check presigned URLs).
 */
export const isPdfUrl = (url: string | null | undefined): boolean => {
  if (!url) return false;
  const path = url.split('?')[0];
  return path.toLowerCase().endsWith('.pdf');
};

/**
 * Check if file is image
 */
export const isImage = (contentType: string | undefined): boolean => {
  if (!contentType) return false;
  return contentType.startsWith('image/');
};
