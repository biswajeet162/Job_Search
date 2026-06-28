import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'ctcFormat', standalone: true })
export class CtcFormatPipe implements PipeTransform {
  transform(value: number | null | undefined): string {
    if (value == null) {
      return '—';
    }

    if (value >= 100000) {
      return `₹${(value / 100000).toFixed(1)} LPA`;
    }

    return `₹${value.toLocaleString('en-IN')}`;
  }
}
