import { delay, Observable, of } from 'rxjs';

export const MOCK_API_DELAY_MS = 600;

export function mockDelay<T>(data: T, ms = MOCK_API_DELAY_MS): Observable<T> {
  return of(data).pipe(delay(ms));
}
