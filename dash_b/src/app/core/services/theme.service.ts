import { Injectable, Renderer2, RendererFactory2, Inject } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { BehaviorSubject, Observable } from 'rxjs';
import { Theme } from '../models/ui.model';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private renderer: Renderer2;

  private readonly themes: Theme[] = [
    {
      name: 'indigo-pink',
      primary: '#3f51b5',
      accent: '#e91e63',
      warn: '#f44336',
      isDark: false
    },
    {
      name: 'purple-green',
      primary: '#9c27b0',
      accent: '#4caf50',
      warn: '#ff9800',
      isDark: false
    },
    {
      name: 'pink-blue-grey',
      primary: '#e91e63',
      accent: '#607d8b',
      warn: '#f44336',
      isDark: true
    },
    {
      name: 'deeppurple-amber',
      primary: '#673ab7',
      accent: '#ffc107',
      warn: '#f44336',
      isDark: true
    }
  ];

  private get defaultTheme(): Theme {
    return this.themes[0];
  }

  private currentThemeSubject = new BehaviorSubject<Theme>(this.defaultTheme);
  public currentTheme$ = this.currentThemeSubject.asObservable();

  constructor(
    private rendererFactory: RendererFactory2,
    @Inject(DOCUMENT) private document: Document
  ) {
    this.renderer = this.rendererFactory.createRenderer(null, null);
    this.loadSavedTheme();
  }

  getThemes(): Theme[] {
    return [...this.themes];
  }

  getCurrentTheme(): Theme {
    return this.currentThemeSubject.value;
  }

  setTheme(themeName: string): void {
    const theme = this.themes.find(t => t.name === themeName);
    if (theme) {
      this.applyTheme(theme);
      this.currentThemeSubject.next(theme);
      this.saveTheme(theme);
    }
  }

  toggleDarkMode(): void {
    const currentTheme = this.getCurrentTheme();
    const darkTheme = this.themes.find(t => t.isDark !== currentTheme.isDark);
    if (darkTheme) {
      this.setTheme(darkTheme.name);
    }
  }

  isDarkMode(): boolean {
    return this.getCurrentTheme().isDark;
  }

  private applyTheme(theme: Theme): void {
    // Remove existing theme classes
    this.themes.forEach(t => {
      this.renderer.removeClass(this.document.body, t.name);
    });

    // Add new theme class
    this.renderer.addClass(this.document.body, theme.name);

    // Update CSS custom properties
    this.document.documentElement.style.setProperty('--primary-color', theme.primary);
    this.document.documentElement.style.setProperty('--accent-color', theme.accent);
    this.document.documentElement.style.setProperty('--warn-color', theme.warn);

    // Update dark mode class
    if (theme.isDark) {
      this.renderer.addClass(this.document.body, 'dark-theme');
    } else {
      this.renderer.removeClass(this.document.body, 'dark-theme');
    }
  }

  private saveTheme(theme: Theme): void {
    localStorage.setItem('selectedTheme', theme.name);
  }

  private loadSavedTheme(): void {
    const savedThemeName = localStorage.getItem('selectedTheme');
    if (savedThemeName) {
      const savedTheme = this.themes.find(t => t.name === savedThemeName);
      if (savedTheme) {
        this.applyTheme(savedTheme);
        this.currentThemeSubject.next(savedTheme);
        return;
      }
    }
    // Apply default theme
    this.applyTheme(this.defaultTheme);
  }
}