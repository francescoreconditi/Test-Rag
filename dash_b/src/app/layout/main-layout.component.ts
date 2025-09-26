import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HeaderComponent } from './header/header.component';
import { SidebarComponent } from './sidebar/sidebar.component';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [RouterOutlet, HeaderComponent, SidebarComponent],
  template: `
    <app-header></app-header>
    <app-sidebar>
      <main class="main-content">
        <router-outlet></router-outlet>
      </main>
    </app-sidebar>
  `,
  styles: [`
    .main-content {
      padding-top: 64px;
      height: 100vh;
      overflow-y: auto;
      background: #fafafa;
    }

    // Dark theme styles
    :host-context(.dark-theme) .main-content {
      background: #303030;
      color: #ffffff;
    }

    // Responsive adjustments
    @media (max-width: 768px) {
      .main-content {
        padding-top: 56px;
      }
    }
  `]
})
export class MainLayoutComponent {}