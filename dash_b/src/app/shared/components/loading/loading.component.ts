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
          <div class="loading-animation">
            <div class="loading-circle"></div>
            <div class="loading-circle"></div>
            <div class="loading-circle"></div>
          </div>
          <div *ngIf="message" class="loading-message">
            {{ message }}
          </div>
          <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
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
      background: rgba(0, 0, 0, 0.85);
      backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      animation: fadeIn 0.3s ease-in;
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .overlay-content {
      background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
      color: #2c3e50;
      padding: 60px 80px;
      border-radius: 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 32px;
      box-shadow:
        0 20px 60px rgba(0, 0, 0, 0.3),
        0 0 0 1px rgba(255, 255, 255, 0.1) inset;
      min-width: 400px;
      animation: slideUp 0.4s ease-out;
      position: relative;
      overflow: hidden;
    }

    .overlay-content::before {
      content: '';
      position: absolute;
      top: -50%;
      left: -50%;
      width: 200%;
      height: 200%;
      background: linear-gradient(
        45deg,
        transparent,
        rgba(103, 126, 234, 0.05),
        transparent
      );
      transform: rotate(45deg);
      animation: shimmer 3s infinite;
    }

    @keyframes slideUp {
      from {
        transform: translateY(30px);
        opacity: 0;
      }
      to {
        transform: translateY(0);
        opacity: 1;
      }
    }

    @keyframes shimmer {
      0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
      100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
    }

    .loading-animation {
      display: flex;
      gap: 12px;
      height: 60px;
      align-items: center;
    }

    .loading-circle {
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      animation: bounce 1.4s ease-in-out infinite both;
    }

    .loading-circle:nth-child(1) {
      animation-delay: -0.32s;
    }

    .loading-circle:nth-child(2) {
      animation-delay: -0.16s;
    }

    @keyframes bounce {
      0%, 80%, 100% {
        transform: scale(0.8);
        opacity: 0.5;
      }
      40% {
        transform: scale(1.2);
        opacity: 1;
      }
    }

    /* Dark theme support */
    :host-context(.dark-theme) .overlay-content,
    :host-context([data-theme="dark"]) .overlay-content {
      background: linear-gradient(145deg, #2a2a2a 0%, #1e1e1e 100%);
      box-shadow:
        0 20px 60px rgba(0, 0, 0, 0.7),
        0 0 0 1px rgba(255, 255, 255, 0.05) inset;
    }

    :host-context(.dark-theme) .loading-circle,
    :host-context([data-theme="dark"]) .loading-circle {
      background: linear-gradient(135deg, #667eea 0%, #9f7aea 100%);
    }

    :host-context(.dark-theme) .loading-dots span,
    :host-context([data-theme="dark"]) .loading-dots span {
      background: #9f7aea;
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
      font-size: 1.3rem;
      color: #2c3e50;
      text-align: center;
      font-weight: 600;
      letter-spacing: 0.5px;
      position: relative;
      z-index: 1;
    }

    .loading-dots {
      display: flex;
      gap: 8px;
      margin-top: -16px;
    }

    .loading-dots span {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #667eea;
      animation: pulse 1.4s ease-in-out infinite;
    }

    .loading-dots span:nth-child(1) {
      animation-delay: 0s;
    }

    .loading-dots span:nth-child(2) {
      animation-delay: 0.2s;
    }

    .loading-dots span:nth-child(3) {
      animation-delay: 0.4s;
    }

    @keyframes pulse {
      0%, 60%, 100% {
        opacity: 0.3;
        transform: scale(0.8);
      }
      30% {
        opacity: 1;
        transform: scale(1.2);
      }
    }

    /* Dark theme text colors */
    :host-context(.dark-theme) .loading-message,
    :host-context([data-theme="dark"]) .loading-message {
      color: #ffffff;
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