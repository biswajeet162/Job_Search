import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ResumeService, ResumeUploadResult } from '../../../core/services/resume.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [RouterLink, LoadingSpinnerComponent, PageHeaderComponent],
  templateUrl: './upload.component.html',
  styleUrl: './upload.component.scss'
})
export class UploadComponent {
  selectedFile?: File;
  parsing = false;
  result?: ResumeUploadResult;
  error = '';

  constructor(private readonly resumeService: ResumeService) {}

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedFile = input.files?.[0];
    this.result = undefined;
    this.error = '';
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    const file = event.dataTransfer?.files?.[0];
    if (file) {
      this.selectedFile = file;
      this.result = undefined;
      this.error = '';
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
  }

  upload(): void {
    if (!this.selectedFile) {
      this.error = 'Please select a resume file first.';
      return;
    }

    this.parsing = true;
    this.error = '';
    this.resumeService.uploadAndParse(this.selectedFile).subscribe({
      next: (result) => {
        this.result = result;
        this.parsing = false;
      },
      error: () => {
        this.error = 'Failed to parse resume. Please try again.';
        this.parsing = false;
      }
    });
  }
}
