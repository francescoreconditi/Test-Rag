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
          <mat-spinner [diameter]="spinnerSize" [color]="color"></mat-spinner>
          <div *ngIf="message" class="loading-message">{{ message }}</div>
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
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
    }

    .overlay-content {
      background: white;
      padding: 32px;
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
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
      font-size: 0.9rem;
      color: #666;
      text-align: center;
      font-weight: 500;
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