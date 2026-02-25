// frontend/lib/retry-utils.ts

export interface RetryOptions {
  maxRetries?: number;
  delay?: number; // Initial delay in ms
  backoff?: 'linear' | 'exponential'; // Backoff strategy
  shouldRetry?: (error: Error, attempt: number) => boolean; // Function to determine if we should retry
}

export const withRetry = async <T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> => {
  const {
    maxRetries = 3,
    delay = 1000,
    backoff = 'exponential',
    shouldRetry = () => true
  } = options;

  let lastError: Error;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      // Don't retry if shouldRetry returns false
      if (!shouldRetry(lastError, attempt)) {
        throw lastError;
      }

      // If this was the last attempt, throw the error
      if (attempt === maxRetries) {
        throw lastError;
      }

      // Calculate delay based on backoff strategy
      let currentDelay: number;
      if (backoff === 'exponential') {
        currentDelay = delay * Math.pow(2, attempt);
      } else {
        currentDelay = delay * (attempt + 1);
      }

      // Add some jitter to avoid thundering herd problem
      currentDelay += Math.random() * 1000;

      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, currentDelay));
    }
  }

  // This should never be reached, but TypeScript requires it
  throw lastError!;
};

// Specific retry functions for different types of operations
export const retryNetworkCall = async <T>(
  fn: () => Promise<T>,
  options: Omit<RetryOptions, 'shouldRetry'> = {}
): Promise<T> => {
  return withRetry(fn, {
    ...options,
    shouldRetry: (error) => {
      // Do not retry client errors (4xx) — they won't change on retry
      const status = (error as { status?: number }).status;
      if (status !== undefined && status >= 400 && status < 500) {
        return false;
      }
      // Retry on network errors, timeouts, and server errors (5xx)
      return (
        status === undefined ||
        status === 0 ||
        status >= 500 ||
        error.message.includes('Network error') ||
        error.message.includes('timeout')
      );
    }
  });
};

// Hook for use in React components
export const useRetry = () => {
  const retryOperation = async <T>(
    operation: () => Promise<T>,
    options: RetryOptions = {}
  ): Promise<T> => {
    return withRetry(operation, options);
  };

  return { retryOperation };
};