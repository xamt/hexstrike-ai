/** A bounded, public record-service error without request contents or credentials. */
export class RecordError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'RecordError';
    this.code = code;
  }
}

/** Stop an operation with a stable error code. */
export function fail(code, message) {
  throw new RecordError(code, message);
}

/** Convert expected failures and hide filesystem internals for unexpected failures. */
export function failure(error) {
  if (error instanceof RecordError) return { success: false, error: { code: error.code, message: error.message } };
  if (error?.code === 'ELOOP') return { success: false, error: { code: 'UNSAFE_PATH', message: '拒绝符号链接路径。' } };
  return { success: false, error: { code: 'STORAGE_ERROR', message: '记录存储操作失败，请检查目录权限、磁盘空间和记录完整性。' } };
}
