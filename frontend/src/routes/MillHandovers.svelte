<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import { handoverSlotLabel, millStatusLabel } from '../lib/labels';
  import type { HandoverSlot, Mill, MillHandover, MillStatus } from '../lib/types';

  let rows: MillHandover[] = [];
  let mills: Mill[] = [];
  let error = '';
  let editingId: number | null = null;
  let editSnapshot: MillStatus | null = null;

  let filterMillId = '';
  let filterDate = '';

  function todayStr(): string {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 10);
  }

  let form = {
    millId: '',
    shiftDate: todayStr(),
    slot: 'morning' as HandoverSlot,
    fromOperator: '',
    toOperator: '',
    note: '',
  };

  $: selectedMill = mills.find((m) => m.id === Number(form.millId));
  $: snapshotStatus = editingId ? editSnapshot : (selectedMill?.status ?? null);

  async function load() {
    error = '';
    try {
      const params = new URLSearchParams();
      if (filterMillId) params.set('millId', filterMillId);
      if (filterDate) params.set('date', filterDate);
      const qs = params.toString();
      [rows, mills] = await Promise.all([
        api<MillHandover[]>(`/mill-handovers${qs ? `?${qs}` : ''}`),
        api<Mill[]>('/mills'),
      ]);
      if (!form.millId && mills[0]) form.millId = String(mills[0].id);
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
    }
  }

  onMount(load);

  function millLabel(id: number): string {
    const m = mills.find((x) => x.id === id);
    return m ? `${m.millCode} (#${m.id})` : `#${id}`;
  }

  function reset() {
    form = {
      millId: mills[0] ? String(mills[0].id) : '',
      shiftDate: todayStr(),
      slot: 'morning',
      fromOperator: '',
      toOperator: '',
      note: '',
    };
    editingId = null;
    editSnapshot = null;
  }

  function edit(row: MillHandover) {
    editingId = row.id;
    editSnapshot = row.millStatusSnapshot;
    form = {
      millId: String(row.millId),
      shiftDate: row.shiftDate,
      slot: row.slot,
      fromOperator: row.fromOperator,
      toOperator: row.toOperator,
      note: row.note || '',
    };
  }

  async function save() {
    error = '';
    const payload = {
      millId: Number(form.millId),
      shiftDate: form.shiftDate,
      slot: form.slot,
      fromOperator: form.fromOperator,
      toOperator: form.toOperator,
      note: form.note,
    };
    try {
      if (editingId) {
        await api(`/mill-handovers/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        });
      } else {
        await api('/mill-handovers', { method: 'POST', body: JSON.stringify(payload) });
      }
      reset();
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : '保存失败';
    }
  }

  async function remove(id: number) {
    if (!confirm('确认删除该交接记录？')) return;
    try {
      await api(`/mill-handovers/${id}`, { method: 'DELETE' });
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : '删除失败';
    }
  }
</script>

<header class="page-head">
  <h1>交接班</h1>
  <p>同一机台同一日期同一班次仅一条；创建时自动记录机台当前状态快照</p>
</header>

{#if error}
  <div class="err">{error}</div>
{/if}

<section class="panel">
  <h2>{editingId ? '编辑交接' : '新增交接'}</h2>
  <div class="fields">
    <div class="field">
      <label>研磨机
        <select bind:value={form.millId}>
          {#each mills as m}
            <option value={String(m.id)}>{m.millCode}</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="field"><label>交接日期<input type="date" bind:value={form.shiftDate} /></label></div>
    <div class="field">
      <label>班次
        <select bind:value={form.slot}>
          <option value="morning">早班</option>
          <option value="afternoon">中班</option>
          <option value="night">夜班</option>
        </select>
      </label>
    </div>
    <div class="field">
      <span class="snap-label">机台状态快照{editingId ? '（创建时记录，不可改）' : '（保存时自动记录当前状态）'}</span>
      <div class="snapshot">
        {#if snapshotStatus}
          <span class="badge {snapshotStatus}">{millStatusLabel[snapshotStatus]}</span>
        {:else}
          <span class="muted">选择研磨机后自动带出</span>
        {/if}
      </div>
    </div>
    <div class="field"><label>交班人<input bind:value={form.fromOperator} /></label></div>
    <div class="field"><label>接班人<input bind:value={form.toOperator} /></label></div>
    <div class="field full"><label>备注<textarea rows="2" bind:value={form.note} /></label></div>
  </div>
  <div class="actions">
    <button class="btn-primary" on:click={save}>{editingId ? '保存' : '创建'}</button>
    {#if editingId}
      <button class="btn-ghost" on:click={reset}>取消</button>
    {/if}
  </div>
</section>

<section class="panel">
  <h2>筛选</h2>
  <div class="fields">
    <div class="field">
      <label>研磨机
        <select bind:value={filterMillId} on:change={load}>
          <option value="">全部机台</option>
          {#each mills as m}
            <option value={String(m.id)}>{m.millCode}</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="field">
      <label>日期
        <input type="date" bind:value={filterDate} on:change={load} />
      </label>
    </div>
  </div>
</section>

<section class="panel">
  <table class="data-table">
    <thead>
      <tr>
        <th>ID</th>
        <th>研磨机</th>
        <th>日期</th>
        <th>班次</th>
        <th>交班</th>
        <th>接班</th>
        <th>状态快照</th>
        <th>备注</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {#each rows as row}
        <tr>
          <td>{row.id}</td>
          <td>{millLabel(row.millId)}</td>
          <td>{row.shiftDate}</td>
          <td>{handoverSlotLabel[row.slot]}</td>
          <td>{row.fromOperator}</td>
          <td>{row.toOperator}</td>
          <td><span class="badge {row.millStatusSnapshot}">{millStatusLabel[row.millStatusSnapshot]}</span></td>
          <td>{row.note || '—'}</td>
          <td class="ops">
            <button class="link-btn" on:click={() => edit(row)}>编辑</button>
            <button class="link-btn danger" on:click={() => remove(row.id)}>删除</button>
          </td>
        </tr>
      {:else}
        <tr><td colspan="9">暂无数据</td></tr>
      {/each}
    </tbody>
  </table>
</section>

<style>
  .snap-label {
    display: block;
    font-size: 0.8rem;
    color: var(--steel);
    margin-bottom: 0.3rem;
  }

  .snapshot {
    display: flex;
    align-items: center;
    min-height: 2.35rem;
    padding: 0.4rem 0.65rem;
    border: 1px dashed var(--line);
    background: rgba(0, 0, 0, 0.2);
  }
</style>
