import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { environment } from '../../../../environments/environment';
import { FileUploadProgress } from '../../../core/models/ui.model';

@Component({
  selector: 'app-file-upload',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatListModule,
    MatChipsModule,
    MatTooltipModule
  ],
  template: `
    <mat-card class="file-upload-card">
      <mat-card-header>
        <mat-card-title>{{ title }}</mat-card-title>
        <mat-card-subtitle>{{ subtitle }}</mat-card-subtitle>
      </mat-card-header>

      <mat-card-content>
        <!-- Drop Zone -->
        <div
          class="drop-zone"
          [class.drag-over]="isDragOver"
          [class.disabled]="disabled"
          (click)="triggerFileInput()"
          (dragover)="onDragOver($event)"
          (dragleave)="onDragLeave($event)"
          (drop)="onDrop($event)">

          <input
            #fileInput
            type="file"
            [multiple]="multiple"
            [accept]="acceptedTypes"
            (change)="onFileSelect($event)"
            style="display: none;">

          <div class="drop-zone-content">
            <mat-icon class="upload-icon">cloud_upload</mat-icon>
            <div class="upload-text">
              <p class="primary-text">{{ dropZoneText }}</p>
              <p class="secondary-text">{{ supportedFormats }}</p>
            </div>
            <button mat-raised-button color="primary" type="button" [disabled]="disabled">
              Seleziona File
            </button>
          </div>
        </div>

        <!-- File List -->
        <div *ngIf="uploadFiles.length > 0" class="file-list">
          <h4>File selezionati ({{ uploadFiles.length }})</h4>
          <mat-list>
            <mat-list-item *ngFor="let fileProgress of uploadFiles">
              <mat-icon matListItemIcon [ngSwitch]="fileProgress.status">
                <ng-container *ngSwitchCase="'pending'">description</ng-container>
                <ng-container *ngSwitchCase="'uploading'">upload</ng-container>
                <ng-container *ngSwitchCase="'completed'">check_circle</ng-container>
                <ng-container *ngSwitchCase="'error'">error</ng-container>
              </mat-icon>

              <div matListItemTitle>{{ fileProgress.file.name }}</div>
              <div matListItemLine class="file-details">
                {{ formatFileSize(fileProgress.file.size) }} •
                {{ getFileType(fileProgress.file.name) }}
                <span *ngIf="fileProgress.error" class="error-message">
                  • {{ fileProgress.error }}
                </span>
              </div>

              <!-- Progress Bar -->
              <mat-progress-bar
                *ngIf="fileProgress.status === 'uploading'"
                [value]="fileProgress.progress"
                mode="determinate"
                class="file-progress">
              </mat-progress-bar>

              <!-- Remove Button -->
              <button
                mat-icon-button
                (click)="removeFile(fileProgress)"
                [disabled]="fileProgress.status === 'uploading'"
                matTooltip="Rimuovi file">
                <mat-icon>close</mat-icon>
              </button>
            </mat-list-item>
          </mat-list>
        </div>

      </mat-card-content>

      <mat-card-actions *ngIf="uploadFiles.length > 0">
        <button
          mat-raised-button
          color="primary"
          (click)="startUpload()"
          [disabled]="disabled || isUploading || !hasValidFiles">
          <mat-icon>cloud_upload</mat-icon>
          Carica File ({{ validFileCount }})
        </button>
        <button
          mat-button
          (click)="clearAll()"
          [disabled]="isUploading">
          <mat-icon>clear_all</mat-icon>
          Cancella Tutto
        </button>
      </mat-card-actions>
    </mat-card>
  `,
  styles: [`
    .file-upload-card {
      margin: 16px 0;
    }

    .drop-zone {
      border: 2px dashed #ccc;
      border-radius: 8px;
      padding: 32px;
      text-align: center;
      cursor: pointer;
      transition: all 0.3s ease;
      background: #fafafa;

      &:hover:not(.disabled) {
        border-color: #3f51b5;
        background: #f5f5f5;
      }

      &.drag-over {
        border-color: #3f51b5;
        background: #e8eaf6;
        transform: scale(1.02);
      }

      &.disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
    }

    .drop-zone-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
    }

    .upload-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #3f51b5;
    }

    .upload-text {
      .primary-text {
        font-size: 1.1rem;
        font-weight: 500;
        margin: 0 0 8px 0;
        color: #333;
      }

      .secondary-text {
        font-size: 0.9rem;
        color: #666;
        margin: 0;
      }
    }

    .file-list {
      margin-top: 24px;

      h4 {
        margin: 0 0 16px 0;
        font-size: 1rem;
        font-weight: 500;
      }
    }

    .file-details {
      font-size: 0.8rem;
      color: #666;
    }

    .error-message {
      color: #f44336;
      font-weight: 500;
    }

    .file-progress {
      margin-top: 8px;
    }

    .file-info {
      margin-top: 24px;
      padding: 16px;
      background: #f5f5f5;
      border-radius: 4px;

      h5 {
        margin: 0 0 12px 0;
        font-size: 0.9rem;
        font-weight: 500;
      }

      .format-chips {
        margin-bottom: 12px;
      }

      .size-limit {
        font-size: 0.8rem;
        color: #666;
        margin: 0;
      }
    }

    mat-card-actions {
      display: flex;
      gap: 8px;
      padding: 16px 24px;
    }

    @media (max-width: 768px) {
      .drop-zone {
        padding: 24px 16px;
      }

      .upload-text .primary-text {
        font-size: 1rem;
      }

      .upload-text .secondary-text {
        font-size: 0.8rem;
      }
    }
  `]
})
export class FileUploadComponent implements OnInit {
  @Input() title = 'Carica Documenti';
  @Input() subtitle = 'Seleziona o trascina i file per caricarli';
  @Input() multiple = true;
  @Input() disabled = false;
  @Input() showFileInfo = true;
  @Input() maxFileSize = environment.limits.maxFileSize;
  @Input() maxFiles = environment.limits.maxFiles;
  @Input() allowedTypes = environment.limits.allowedFileTypes;

  @Output() filesSelected = new EventEmitter<File[]>();
  @Output() uploadStarted = new EventEmitter<FileUploadProgress[]>();
  @Output() uploadProgress = new EventEmitter<FileUploadProgress>();
  @Output() uploadCompleted = new EventEmitter<FileUploadProgress[]>();
  @Output() uploadError = new EventEmitter<{ file: File; error: string }>();

  uploadFiles: FileUploadProgress[] = [];
  isDragOver = false;
  isUploading = false;

  get dropZoneText(): string {
    return this.multiple
      ? 'Trascina qui i file o clicca per selezionare'
      : 'Trascina qui il file o clicca per selezionare';
  }

  get supportedFormats(): string {
    return `Supportati: ${this.allowedTypes.map(t => t.toUpperCase()).join(', ')}`;
  }

  get acceptedTypes(): string {
    return this.allowedTypes.map(type => `.${type}`).join(',');
  }

  get hasValidFiles(): boolean {
    return this.uploadFiles.some(f => f.status === 'pending');
  }

  get validFileCount(): number {
    return this.uploadFiles.filter(f => f.status === 'pending').length;
  }

  ngOnInit(): void {}

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    if (!this.disabled) {
      this.isDragOver = true;
    }
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver = false;

    if (this.disabled) return;

    const files = Array.from(event.dataTransfer?.files || []);
    this.handleFiles(files);
  }

  triggerFileInput(): void {
    if (this.disabled) return;
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fileInput?.click();
  }

  onFileSelect(event: Event): void {
    const target = event.target as HTMLInputElement;
    const files = Array.from(target.files || []);
    this.handleFiles(files);
    target.value = ''; // Reset input
  }

  private handleFiles(files: File[]): void {
    if (files.length === 0) return;

    // Validate file count
    const currentFileCount = this.uploadFiles.length;
    const totalFiles = currentFileCount + files.length;

    if (totalFiles > this.maxFiles) {
      const maxAdditional = this.maxFiles - currentFileCount;
      files = files.slice(0, maxAdditional);
    }

    // Process each file
    const newFileProgresses: FileUploadProgress[] = [];

    files.forEach(file => {
      const validation = this.validateFile(file);
      const fileProgress: FileUploadProgress = {
        file,
        progress: 0,
        status: validation.isValid ? 'pending' : 'error',
        error: validation.error
      };

      newFileProgresses.push(fileProgress);
    });

    this.uploadFiles.push(...newFileProgresses);
    this.filesSelected.emit(files);
  }

  private validateFile(file: File): { isValid: boolean; error?: string } {
    // Check file size
    if (file.size > this.maxFileSize) {
      return {
        isValid: false,
        error: `File troppo grande (max ${this.formatFileSize(this.maxFileSize)})`
      };
    }

    // Check file type
    const fileExtension = file.name.split('.').pop()?.toLowerCase();
    if (!fileExtension || !this.allowedTypes.includes(fileExtension)) {
      return {
        isValid: false,
        error: `Tipo file non supportato`
      };
    }

    return { isValid: true };
  }

  removeFile(fileProgress: FileUploadProgress): void {
    const index = this.uploadFiles.indexOf(fileProgress);
    if (index > -1) {
      this.uploadFiles.splice(index, 1);
    }
  }

  clearAll(): void {
    this.uploadFiles = [];
  }

  startUpload(): void {
    const pendingFiles = this.uploadFiles.filter(f => f.status === 'pending');
    if (pendingFiles.length === 0) return;

    this.isUploading = true;
    this.uploadStarted.emit(pendingFiles);

    // Simulate upload progress for each file
    pendingFiles.forEach(fileProgress => {
      this.simulateUpload(fileProgress);
    });
  }

  private simulateUpload(fileProgress: FileUploadProgress): void {
    fileProgress.status = 'uploading';
    fileProgress.progress = 0;

    const interval = setInterval(() => {
      fileProgress.progress += Math.random() * 15;

      if (fileProgress.progress >= 100) {
        fileProgress.progress = 100;
        fileProgress.status = 'completed';
        clearInterval(interval);

        this.uploadProgress.emit(fileProgress);

        // Check if all uploads are complete
        const stillUploading = this.uploadFiles.some(f => f.status === 'uploading');
        if (!stillUploading) {
          this.isUploading = false;
          this.uploadCompleted.emit(this.uploadFiles.filter(f => f.status === 'completed'));
        }
      } else {
        this.uploadProgress.emit(fileProgress);
      }
    }, 200);
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  getFileType(fileName: string): string {
    return fileName.split('.').pop()?.toUpperCase() || 'Unknown';
  }
}