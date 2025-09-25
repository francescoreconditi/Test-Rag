import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatCardModule } from '@angular/material/card';

@Component({
  selector: 'app-loading',
  standalone: true,
  imports: [
    CommonModule,
    MatProgressSpinnerModule,
    MatProgressBarModule,
    MatCardModule
  ],
  template: `
    <div class="loading-container" [ngClass]="containerClass">
      <!-- Spinner Loading -->
      <div *ngIf="type === 'spinner'" class="spinner-loading">
        <mat-spinner [diameter]="spinnerSize" [color]="color"></mat-spinner>
        <div *ngIf="message" class="loading-message">{{ message }}</div>
      </div>

      <!-- Progress Bar Loading -->
      <div *ngIf="type === 'progress'" class="progress-loading">
        <div *ngIf="message" class="loading-message">{{ message }}</div>
        <mat-progress-bar
          [mode]="progress !== undefined ? 'determinate' : 'indeterminate'"
          [value]="progress"
          [color]="color">
        </mat-progress-bar>
        <div *ngIf="progress !== undefined" class="progress-text">
          {{ progress }}%
        </div>
      </div>

      <!-- Overlay Loading -->
      <div *ngIf="type === 'overlay'" class="overlay-loading">
        <div class="overlay-content">
          <div class="loading-icon-wrapper">
            <mat-spinner [diameter]="spinnerSize" [color]="color"></mat-spinner>
          </div>
          <div *ngIf="message" class="loading-message">
            <span class="loading-text">{{ message }}</span>
            <span class="loading-dots"></span>
          </div>
          <div class="loading-subtext">Attendere prego</div>
        </div>
      </div>

      <!-- Card Loading -->
      <mat-card *ngIf="type === 'card'" class="card-loading">
        <mat-card-content>
          <div class="card-loading-content">
            <mat-spinner [diameter]="spinnerSize" [color]="color"></mat-spinner>
            <div *ngIf="message" class="loading-message">{{ message }}</div>
          </div>
        </mat-card-content>
      </mat-card>

      <!-- Skeleton Loading -->
      <div *ngIf="type === 'skeleton'" class="skeleton-loading">
        <div class="skeleton-item" *ngFor="let item of skeletonItems"></div>
      </div>
    </div>
  `,
  styles: [`
    .loading-container {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
    }

    .spinner-loading,
    .progress-loading {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
    }

    .overlay-loading {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(4px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      animation: fadeIn 0.2s ease-in;
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .overlay-content {
      background: var(--overlay-bg, white);
      color: var(--overlay-text, #333);
      padding: 48px 56px;
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 24px;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
      min-width: 320px;
      animation: scaleIn 0.3s ease-out;
    }

    @keyframes scaleIn {
      from { transform: scale(0.9); opacity: 0; }
      to { transform: scale(1); opacity: 1; }
    }

    .loading-icon-wrapper {
      position: relative;
      padding: 8px;
    }

    /* Dark theme support */
    :host-context(.dark-theme) .overlay-content,
    :host-context([data-theme="dark"]) .overlay-content {
      --overlay-bg: #2a2a2a;
      --overlay-text: #ffffff;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
    }

    .card-loading {
      width: 100%;
      margin: 16px 0;
    }

    .card-loading-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      padding: 16px;
    }

    .loading-message {
      font-size: 1.1rem;
      color: var(--overlay-text, #333);
      text-align: center;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .loading-text {
      letter-spacing: 0.5px;
    }

    .loading-dots::after {
      content: '...';
      display: inline-block;
      animation: ellipsis 1.5s infinite;
      width: 20px;
      text-align: left;
    }

    @keyframes ellipsis {
      0% { content: '.'; }
      33% { content: '..'; }
      66% { content: '...'; }
      100% { content: '.'; }
    }

    .loading-subtext {
      font-size: 0.85rem;
      color: var(--overlay-text, #666);
      opacity: 0.8;
      margin-top: -8px;
    }

    /* Dark theme text colors */
    :host-context(.dark-theme) .loading-message,
    :host-context([data-theme="dark"]) .loading-message {
      color: #ffffff;
    }

    :host-context(.dark-theme) .loading-subtext,
    :host-context([data-theme="dark"]) .loading-subtext {
      color: #cccccc;
    }

    .progress-text {
      font-size: 0.8rem;
      color: #999;
      text-align: center;
    }

    .skeleton-loading {
      width: 100%;
      padding: 16px;
    }

    .skeleton-item {
      height: 20px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: skeleton-wave 2s infinite;
      margin-bottom: 12px;
      border-radius: 4px;

      &:last-child {
        margin-bottom: 0;
        width: 60%;
      }
    }

    @keyframes skeleton-wave {
      0% {
        background-position: -200% 0;
      }
      100% {
        background-position: 200% 0;
      }
    }

    .fullscreen {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      height: 100vh;
      background: white;
      z-index: 1000;
    }

    .inline {
      padding: 20px;
    }

    .centered {
      min-height: 200px;
    }
  `]
})
export class LoadingComponent {
  @Input() type: 'spinner' | 'progress' | 'overlay' | 'card' | 'skeleton' = 'spinner';
  @Input() message?: string;
  @Input() progress?: number;
  @Input() color: 'primary' | 'accent' | 'warn' = 'primary';
  @Input() spinnerSize: number = 50;
  @Input() containerClass?: string;
  @Input() skeletonItems: number[] = [1, 2, 3, 4, 5];
}