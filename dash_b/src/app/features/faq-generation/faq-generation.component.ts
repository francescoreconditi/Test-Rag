import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-faq-generation',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule],
  template: `
    <div class="container">
      <mat-card>
        <mat-card-header>
          <mat-card-title>❓ Generazione FAQ</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <p>Funzionalità di generazione FAQ in sviluppo...</p>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .container { padding: 24px; }
  `]
})
export class FaqGenerationComponent {}