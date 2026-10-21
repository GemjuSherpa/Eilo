import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { StateEvent } from '@eilo/contracts';
import type { DisplayPreferences } from './ControlClient';
import { effectiveDisplay } from './DisplaySettings';
import { Action, styles, type Colors } from './Onboarding';
import {
  samePresentationIdentity,
  SpokenReply,
  type SpokenPresentation,
} from './SpokenPresentation';

type Context = Pick<
  StateEvent,
  'sessionId' | 'operationId' | 'generation' | 'privacyEpoch'
>;
export type ResultKind = 'place' | 'article' | 'weather' | 'video';
export interface ResultCardData {
  id: string;
  kind: ResultKind;
  title: string;
  summary: string;
  source: { name: string; url: string };
  details: { label: string; value: string }[];
  media: {
    images: 'available' | 'unavailable';
    video: 'available' | 'unavailable';
  };
}
const id =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
function closed(
  value: unknown,
  keys: string[],
): value is Record<string, unknown> {
  return (
    !!value &&
    typeof value === 'object' &&
    Object.getPrototypeOf(value) === Object.prototype &&
    Reflect.ownKeys(value).length === keys.length &&
    Reflect.ownKeys(value).every(
      key => typeof key === 'string' && keys.includes(key),
    ) &&
    Object.values(Object.getOwnPropertyDescriptors(value)).every(descriptor =>
      Object.hasOwn(descriptor, 'value'),
    )
  );
}
function text(value: unknown, limit: number): value is string {
  return (
    typeof value === 'string' &&
    value.trim().length > 0 &&
    value.length <= limit &&
    !Array.from(value).some(
      character =>
        character.charCodeAt(0) < 32 &&
        ![9, 10, 13].includes(character.charCodeAt(0)),
    ) &&
    !/<[^>]*>/.test(value)
  );
}
/** Display attribution only. This is not permission to request/open this URL. */
export function sourceHost(value: unknown): string | null {
  if (typeof value !== 'string' || value.length > 1024) {
    return null;
  }
  const match =
    /^https:\/\/([a-z0-9](?:[a-z0-9.-]*[a-z0-9])?)(?:[/?#][^\s\\]*)?$/i.exec(
      value,
    );
  if (!match) {
    return null;
  }
  const host = match[1].toLowerCase();
  if (
    host.length > 253 ||
    !/\.[a-z]{2,63}$/.test(host) ||
    host
      .split('.')
      .some(
        part =>
          !part ||
          part.length > 63 ||
          part.startsWith('-') ||
          part.endsWith('-'),
      ) ||
    /(?:^|\.)(localhost|local|internal|test|invalid)$/.test(host)
  ) {
    return null;
  }
  return host;
}
/** Strict bounded presentation metadata; factual truth and network authorization remain upstream. */
export function parseResultEnvelope(
  value: unknown,
  expected: Context | null,
): ResultCardData[] {
  if (
    !expected ||
    !closed(value, ['context', 'items']) ||
    !closed(value.context, [
      'sessionId',
      'operationId',
      'generation',
      'privacyEpoch',
    ]) ||
    !samePresentationIdentity(value.context as unknown as Context, expected) ||
    !Array.isArray(value.items) ||
    value.items.length > 8
  ) {
    return [];
  }
  const parsed: ResultCardData[] = [];
  for (const row of value.items) {
    if (
      !closed(row, [
        'id',
        'kind',
        'title',
        'summary',
        'source',
        'details',
        'media',
      ]) ||
      typeof row.id !== 'string' ||
      !id.test(row.id) ||
      parsed.some(item => item.id === row.id) ||
      typeof row.kind !== 'string' ||
      !['place', 'article', 'weather', 'video'].includes(row.kind) ||
      !text(row.title, 160) ||
      !text(row.summary, 1024) ||
      !closed(row.source, ['name', 'url']) ||
      !text(row.source.name, 100) ||
      !sourceHost(row.source.url) ||
      !Array.isArray(row.details) ||
      row.details.length > 6 ||
      row.details.some(
        detail =>
          !closed(detail, ['label', 'value']) ||
          !text(detail.label, 64) ||
          !text(detail.value, 256),
      ) ||
      !closed(row.media, ['images', 'video']) ||
      typeof row.media.images !== 'string' ||
      !['available', 'unavailable'].includes(row.media.images) ||
      typeof row.media.video !== 'string' ||
      !['available', 'unavailable'].includes(row.media.video)
    ) {
      return [];
    }
    parsed.push(row as unknown as ResultCardData);
  }
  return parsed;
}

export function ResultCards({
  envelope = null,
  expected,
  spoken,
  preferences,
  colors,
}: {
  envelope?: unknown;
  expected: Context | null;
  spoken: SpokenPresentation | null;
  preferences: DisplayPreferences;
  colors: Colors;
}) {
  const effective = effectiveDisplay(preferences);
  const safeSpoken =
    spoken && expected && samePresentationIdentity(spoken, expected)
      ? spoken
      : null;
  const hasSpoken = !!safeSpoken?.clauses.length;
  const rows = parseResultEnvelope(envelope, expected);
  const key = [
    expected?.sessionId,
    expected?.operationId,
    expected?.generation,
    expected?.privacyEpoch,
    ...rows.map(row => row.id),
  ].join(':');
  const [selection, setSelection] = useState<{
    key: string;
    kind: ResultKind | 'spoken';
  } | null>(null);
  const selected =
    selection?.key === key ? selection.kind : rows[0]?.kind ?? 'spoken';
  if (!effective.text) {
    return null;
  }
  if (!rows.length) {
    return <SpokenReply value={safeSpoken} colors={colors} />;
  }
  return (
    <View testID="result-cards">
      <View style={layout.tabs}>
        <Action
          colors={colors}
          label={hasSpoken ? 'Show spoken answer' : 'Spoken answer unavailable'}
          disabled={!hasSpoken}
          onPress={() => setSelection({ key, kind: 'spoken' })}
        />
        {(['place', 'article', 'weather', 'video'] as const).map(kind => {
          const available = rows.some(row => row.kind === kind);
          const label = {
            place: 'Places',
            article: 'Articles',
            weather: 'Weather',
            video: 'Video results',
          }[kind];
          return (
            <Action
              key={kind}
              colors={colors}
              label={available ? label : `${label} unavailable`}
              disabled={!available}
              onPress={() => setSelection({ key, kind })}
            />
          );
        })}
      </View>
      {selected === 'spoken' ? (
        <SpokenReply value={safeSpoken} colors={colors} />
      ) : (
        rows
          .filter(row => row.kind === selected)
          .map(row => (
            <View
              key={row.id}
              style={[layout.card, { borderColor: colors.boundary }]}
            >
              <Text
                accessibilityRole="header"
                style={[styles.body, { color: colors.text }]}
              >
                {row.title}
              </Text>
              <Text style={[styles.body, { color: colors.text }]}>
                {row.summary}
              </Text>
              {row.details.map((detail, index) => (
                <Text key={index} style={[styles.body, { color: colors.text }]}>
                  {detail.label}: {detail.value}
                </Text>
              ))}
              <Text style={[styles.body, { color: colors.secondary_text }]}>
                Source: {row.source.name} · {sourceHost(row.source.url)}
              </Text>
              {row.media.images === 'available' && (
                <Text style={[styles.body, { color: colors.secondary_text }]}>
                  {effective.images ? 'Images unavailable' : 'Images off'}
                </Text>
              )}
              {(row.kind === 'video' || row.media.video === 'available') && (
                <Text style={[styles.body, { color: colors.secondary_text }]}>
                  {effective.video ? 'Video unavailable' : 'Video off'}
                </Text>
              )}
            </View>
          ))
      )}
    </View>
  );
}
const layout = StyleSheet.create({
  tabs: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  card: { borderWidth: 1, borderRadius: 16, padding: 16, marginVertical: 8 },
});
