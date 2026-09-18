import type { HandoverSlot, MillStatus } from './types';

export const millStatusLabel: Record<MillStatus, string> = {
  grinding: '研磨中',
  idle: '待机',
  wash: '清洗',
};

export const handoverSlotLabel: Record<HandoverSlot, string> = {
  morning: '早班',
  afternoon: '中班',
  night: '夜班',
};
