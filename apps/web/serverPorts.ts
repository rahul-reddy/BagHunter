function port(value: string | undefined, fallback: number): number {
  if (value === undefined) return fallback;
  if (!/^\d{1,5}$/.test(value) || Number(value) < 1 || Number(value) > 65535)
    throw new Error('Local server ports must be integers from 1 to 65535.');
  return Number(value);
}
export const apiPort = port(process.env.BAGHUNTER_API_PORT, 8000);
export const webPort = port(process.env.BAGHUNTER_WEB_PORT, 5173);
