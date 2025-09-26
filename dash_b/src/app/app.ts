import { Component, OnInit, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ThemeService } from './core/services/theme.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
  protected readonly title = signal('RAG Dashboard');

  constructor(private themeService: ThemeService) {}

  ngOnInit(): void {
    // Initialize theme service (loads saved theme)
  }
}
