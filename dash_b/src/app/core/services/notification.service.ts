import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, timer } from 'rxjs';
import { NotificationMessage } from '../models/ui.model';

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private notificationsSubject = new BehaviorSubject<NotificationMessage[]>([]);
  public notifications$ = this.notificationsSubject.asObservable();

  private nextId = 1;

  constructor() {}

  showSuccess(title: string, message: string, autoClose: boolean = true): string {
    return this.addNotification({
      type: 'success',
      title,
      message,
      autoClose,
      duration: 5000
    });
  }

  showError(title: string, message: string, autoClose: boolean = false): string {
    return this.addNotification({
      type: 'error',
      title,
      message,
      autoClose,
      duration: 0
    });
  }

  showWarning(title: string, message: string, autoClose: boolean = true): string {
    return this.addNotification({
      type: 'warning',
      title,
      message,
      autoClose,
      duration: 7000
    });
  }

  showInfo(title: string, message: string, autoClose: boolean = true): string {
    return this.addNotification({
      type: 'info',
      title,
      message,
      autoClose,
      duration: 5000
    });
  }

  removeNotification(id: string): void {
    const currentNotifications = this.notificationsSubject.value;
    const updatedNotifications = currentNotifications.filter(n => n.id !== id);
    this.notificationsSubject.next(updatedNotifications);
  }

  clearAll(): void {
    this.notificationsSubject.next([]);
  }

  private addNotification(config: Partial<NotificationMessage>): string {
    const notification: NotificationMessage = {
      id: `notification-${this.nextId++}`,
      type: config.type || 'info',
      title: config.title || '',
      message: config.message || '',
      timestamp: new Date(),
      autoClose: config.autoClose ?? true,
      duration: config.duration || 5000
    };

    const currentNotifications = this.notificationsSubject.value;
    this.notificationsSubject.next([...currentNotifications, notification]);

    // Auto-remove notification if autoClose is enabled
    if (notification.autoClose && notification.duration && notification.duration > 0) {
      timer(notification.duration).subscribe(() => {
        this.removeNotification(notification.id);
      });
    }

    return notification.id;
  }
}