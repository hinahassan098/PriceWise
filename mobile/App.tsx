import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Image,
  Linking,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";

const STATUS_BAR_HEIGHT =
  Platform.OS === "android" ? StatusBar.currentHeight ?? 28 : 0;
import {
  formatPkr,
  getCities,
  searchProducts,
  suggestProducts,
  wakeApi,
  type CityOption,
  type SearchResult,
  type StoreOffer,
  type Suggestion,
} from "./src/api";

const COLORS = {
  bg: "#faf2f5",
  bgDeep: "#f0dde5",
  ink: "#2a1018",
  inkSoft: "#7a4d5c",
  line: "#e4c4d0",
  panel: "#fff7fa",
  accent: "#9b2d4a",
  accentDeep: "#5c1228",
  accentSoft: "#d97a96",
  blush: "#f3c5d3",
  heroFg: "#fff5f8",
  heroMuted: "#f0c8d4",
  cheapestBg: "rgba(155, 45, 74, 0.10)",
  danger: "#8a1f3a",
};

const CATEGORIES = [
  { label: "Grocery", q: "atta" },
  { label: "Beverages", q: "coke" },
  { label: "Personal Care", q: "lifebuoy" },
  { label: "Household", q: "surf excel" },
  { label: "Snacks", q: "sooper" },
  { label: "Baby Care", q: "pampers" },
];

export default function App() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [flat, setFlat] = useState<StoreOffer[]>([]);
  const [searched, setSearched] = useState(false);
  const [city, setCity] = useState("all");
  const [cities, setCities] = useState<CityOption[]>([
    { id: "all", name: "All Pakistan", nationwide: true },
  ]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  useEffect(() => {
    getCities()
      .then((data) => {
        if (data.cities?.length) setCities(data.cities);
      })
      .catch(() => null);
  }, []);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setSuggestions([]);
      return;
    }
    const timer = setTimeout(() => {
      suggestProducts(q)
        .then((data) => {
          setSuggestions(data.suggestions || []);
          setShowSuggestions(true);
        })
        .catch(() => setSuggestions([]));
    }, 220);
    return () => clearTimeout(timer);
  }, [query]);

  const runSearch = useCallback(async (raw: string, cityOverride?: string) => {
    const q = raw.trim();
    if (!q) return;
    const cityFilter = cityOverride ?? city;
    setQuery(q);
    setShowSuggestions(false);
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      await wakeApi();
      const data = await searchProducts(q, {
        city: cityFilter === "all" ? undefined : cityFilter,
      });
      setResults(data.results || []);
      setFlat(data.all_store_prices || []);
    } catch (err) {
      setResults([]);
      setFlat([]);
      setError(
        err instanceof Error
          ? err.message
          : "Search failed. The API may be waking up — try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [city]);

  const onSearch = useCallback(() => {
    void runSearch(query);
  }, [query, runSearch]);

  const showHome = !searched && !loading;
  const cityLabel =
    city === "all"
      ? "All Pakistan"
      : cities.find((c) => c.name === city)?.name || city;

  return (
    <View style={styles.root}>
      <StatusBar
        barStyle="light-content"
        backgroundColor={COLORS.accentDeep}
        translucent={false}
      />
      <View style={styles.statusBarFill} />
      <SafeAreaView style={styles.safe}>
        <FlatList
          data={showHome ? [] : results}
          keyExtractor={(item, idx) =>
            `${item.variant_id || item.name}-${item.size_label}-${idx}`
          }
          contentContainerStyle={styles.list}
          keyboardShouldPersistTaps="handled"
          ListHeaderComponent={
            <View>
              <LinearGradient
                colors={["#3a0d1c", "#5c1228", "#9b2d4a", "#c45a78"]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.hero}
              >
                <View style={[styles.orb, styles.orbA]} />
                <View style={[styles.orb, styles.orbB]} />

                <View style={styles.heroContent}>
                  <Image
                    source={require("./assets/logo-mark.png")}
                    style={styles.logoMark}
                    accessibilityLabel="PriceWise"
                  />
                  <Text style={styles.brand}>PriceWise</Text>
                  <Text style={styles.headline}>
                    Know the Price. Own the Choice.
                  </Text>

                  <View style={styles.searchBox}>
                    <TextInput
                      value={query}
                      onChangeText={setQuery}
                      placeholder="What do you want to buy?"
                      placeholderTextColor={COLORS.inkSoft}
                      style={styles.input}
                      returnKeyType="search"
                      onSubmitEditing={onSearch}
                      onFocus={() =>
                        suggestions.length > 0 && setShowSuggestions(true)
                      }
                    />
                    <Pressable
                      style={({ pressed }) => [
                        styles.button,
                        pressed && styles.buttonPressed,
                      ]}
                      onPress={onSearch}
                      disabled={loading}
                    >
                      <Text style={styles.buttonText}>
                        {loading ? "…" : "Show Prices"}
                      </Text>
                    </Pressable>
                  </View>

                  {showSuggestions && suggestions.length > 0 ? (
                    <View style={styles.suggestPanel}>
                      {suggestions.slice(0, 8).map((item, idx) => (
                        <Pressable
                          key={`${item.label}-${idx}`}
                          style={styles.suggestRow}
                          onPress={() => {
                            setQuery(item.query || item.label);
                            setShowSuggestions(false);
                          }}
                        >
                          <Text style={styles.suggestLabel} numberOfLines={1}>
                            {item.label}
                          </Text>
                          <Text style={styles.suggestMeta} numberOfLines={1}>
                            {[item.size_label, item.brand]
                              .filter(Boolean)
                              .join(" · ")}
                          </Text>
                        </Pressable>
                      ))}
                    </View>
                  ) : null}
                </View>
              </LinearGradient>

              {showHome ? (
                <View style={styles.categories}>
                  <Text style={styles.sectionKicker}>Browse</Text>
                  <Text style={styles.sectionBrand}>Popular categories</Text>
                  <View style={styles.categoryList}>
                    {CATEGORIES.map((cat) => (
                      <Pressable
                        key={cat.label}
                        style={({ pressed }) => [
                          styles.categoryRow,
                          pressed && styles.categoryPressed,
                        ]}
                        onPress={() => void runSearch(cat.q)}
                      >
                        <Text style={styles.categoryLabel}>{cat.label}</Text>
                        <Text style={styles.categoryChevron}>›</Text>
                      </Pressable>
                    ))}
                  </View>
                </View>
              ) : null}

              {searched ? (
                <View style={styles.resultsHead}>
                  <Text style={styles.resultsTitle}>Search results</Text>
                  <Text style={styles.resultsMeta}>
                    for “{query.trim()}” · {cityLabel}
                    {loading ? " · searching live stores…" : ""}
                  </Text>
                  <Text style={styles.cityLabelDark}>City</Text>
                  <ScrollView
                    horizontal
                    showsHorizontalScrollIndicator={false}
                    contentContainerStyle={styles.cityRow}
                  >
                    {cities.map((c) => {
                      const value = c.nationwide ? "all" : c.name;
                      const active = city === value;
                      return (
                        <Pressable
                          key={c.id}
                          style={[
                            styles.cityChipLight,
                            active && styles.cityChipLightActive,
                          ]}
                          onPress={() => {
                            setCity(value);
                            void runSearch(query, value);
                          }}
                        >
                          <Text
                            style={[
                              styles.cityChipLightText,
                              active && styles.cityChipLightTextActive,
                            ]}
                          >
                            {c.name}
                          </Text>
                        </Pressable>
                      );
                    })}
                  </ScrollView>
                </View>
              ) : null}

              {loading ? (
                <View style={styles.center}>
                  <ActivityIndicator size="large" color={COLORS.accent} />
                  <Text style={styles.muted}>
                    Comparing prices across stores… this can take up to 20
                    seconds on first load.
                  </Text>
                </View>
              ) : null}

              {error ? (
                <View style={styles.errorBox}>
                  <Text style={styles.errorText}>{error}</Text>
                  <Pressable onPress={onSearch}>
                    <Text style={styles.retry}>Tap to retry</Text>
                  </Pressable>
                </View>
              ) : null}

              {!loading && searched && !error && results.length === 0 ? (
                <Text style={styles.mutedEmpty}>
                  No products found. Try another name.
                </Text>
              ) : null}

              {!loading && flat.length > 0 ? (
                <View style={styles.panel}>
                  <Text style={styles.panelTitle}>All store prices</Text>
                  <Text style={styles.panelSub}>
                    Every matching offer from Pakistani stores, cheapest first.
                  </Text>
                  {flat.slice(0, 12).map((row, idx) => (
                    <Pressable
                      key={`${row.retailer_id}-${row.url}-${idx}`}
                      style={[
                        styles.offerRow,
                        idx === 0 && styles.cheapestRow,
                      ]}
                      onPress={() => Linking.openURL(row.url)}
                    >
                      <View style={styles.offerMain}>
                        <Text style={styles.offerStore}>
                          {row.retailer_name}
                        </Text>
                        <Text style={styles.offerName} numberOfLines={1}>
                          {row.product_name}
                        </Text>
                      </View>
                      <View style={styles.offerRight}>
                        <Text style={styles.offerPrice}>
                          {formatPkr(row.price)}
                        </Text>
                        <Text style={styles.buyLink}>Buy</Text>
                      </View>
                    </Pressable>
                  ))}
                </View>
              ) : null}

              {!loading && results.length > 0 ? (
                <Text style={[styles.panelTitle, styles.byProduct]}>
                  By product
                </Text>
              ) : null}
            </View>
          }
          ListEmptyComponent={null}
          renderItem={({ item }) => {
            const offers = item.offers || [];
            return (
              <View style={styles.card}>
                <View style={styles.cardTop}>
                  {item.image_url ? (
                    <Image
                      source={{ uri: item.image_url }}
                      style={styles.image}
                    />
                  ) : (
                    <View style={[styles.image, styles.imagePlaceholder]} />
                  )}
                  <View style={styles.cardBody}>
                    <Text style={styles.productName}>
                      {[item.brand, item.name].filter(Boolean).join(" ")}
                    </Text>
                    <Text style={styles.size}>{item.size_label}</Text>
                    <Text style={styles.stores}>
                      {item.store_count}{" "}
                      {item.store_count === 1 ? "store" : "stores"} compared
                    </Text>
                  </View>
                  <View style={styles.priceCol}>
                    <Text style={styles.cheapestLabel}>Cheapest</Text>
                    <Text style={styles.price}>
                      {formatPkr(item.cheapest.price)}
                    </Text>
                    <Pressable
                      onPress={() => Linking.openURL(item.cheapest.url)}
                    >
                      <Text style={styles.buy}>{item.cheapest.retailer_name}</Text>
                    </Pressable>
                  </View>
                </View>

                {offers.length > 0 ? (
                  <View style={styles.offerTable}>
                    {offers.slice(0, 5).map((offer) => {
                      const isCheapest =
                        offer.retailer_id === item.cheapest.retailer_id &&
                        offer.price === item.cheapest.price;
                      return (
                        <Pressable
                          key={`${offer.retailer_id}-${offer.url}`}
                          style={[
                            styles.miniOffer,
                            isCheapest && styles.cheapestRow,
                          ]}
                          onPress={() => Linking.openURL(offer.url)}
                        >
                          <Text style={styles.miniStore}>
                            {offer.retailer_name}
                          </Text>
                          <Text style={styles.miniPrice}>
                            {formatPkr(offer.price)}
                          </Text>
                          <Text style={styles.buyLink}>Buy</Text>
                        </Pressable>
                      );
                    })}
                  </View>
                ) : null}
              </View>
            );
          }}
          ListFooterComponent={
            searched ? (
              <Pressable
                style={styles.backHome}
                onPress={() => {
                  setSearched(false);
                  setResults([]);
                  setFlat([]);
                  setError(null);
                  setQuery("");
                }}
              >
                <Text style={styles.backHomeText}>← Back to home</Text>
              </Pressable>
            ) : (
              <View style={{ height: 24 }} />
            )
          }
        />
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: COLORS.bg },
  statusBarFill: {
    height: STATUS_BAR_HEIGHT,
    backgroundColor: COLORS.accentDeep,
  },
  safe: { flex: 1, backgroundColor: COLORS.bg },
  list: { paddingBottom: 40 },
  hero: {
    overflow: 'hidden',
    paddingHorizontal: 24,
    paddingTop: 28,
    paddingBottom: 32,
  },
  orb: {
    position: 'absolute',
    borderRadius: 999,
    opacity: 0.55,
  },
  orbA: {
    width: 180,
    height: 180,
    top: -40,
    right: -20,
    backgroundColor: 'rgba(243,197,211,0.35)',
  },
  orbB: {
    width: 140,
    height: 140,
    bottom: 20,
    left: -30,
    backgroundColor: 'rgba(155,45,74,0.45)',
  },
  heroContent: { position: 'relative', zIndex: 1 },
  logoMark: {
    width: 56,
    height: 56,
    borderRadius: 28,
    marginBottom: 16,
  },
  brand: {
    fontFamily: 'serif',
    fontSize: 44,
    fontWeight: '600',
    color: COLORS.heroFg,
    letterSpacing: -1,
    marginBottom: 10,
  },
  headline: {
    fontSize: 20,
    fontWeight: '400',
    color: COLORS.heroFg,
    lineHeight: 28,
    maxWidth: 300,
    marginBottom: 8,
  },
  cityRow: {
    gap: 8,
    paddingBottom: 4,
    marginTop: 8,
  },
  cityLabelDark: {
    marginTop: 14,
    marginBottom: 6,
    color: COLORS.inkSoft,
    fontSize: 13,
    fontWeight: '600',
  },
  cityChipLight: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: COLORS.line,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#fff',
  },
  cityChipLightActive: {
    backgroundColor: COLORS.blush,
    borderColor: COLORS.blush,
  },
  cityChipLightText: {
    color: COLORS.inkSoft,
    fontSize: 13,
    fontWeight: '600',
  },
  cityChipLightTextActive: {
    color: COLORS.accentDeep,
  },
  searchBox: {
    marginTop: 22,
    flexDirection: 'row',
    gap: 8,
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 6,
    borderWidth: 1,
    borderColor: COLORS.line,
  },
  suggestPanel: {
    marginTop: 8,
    backgroundColor: '#fff',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: COLORS.line,
    overflow: 'hidden',
  },
  suggestRow: {
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: COLORS.line,
  },
  suggestLabel: {
    color: COLORS.ink,
    fontWeight: '600',
    fontSize: 14,
  },
  suggestMeta: {
    marginTop: 2,
    color: COLORS.inkSoft,
    fontSize: 12,
  },
  input: {
    flex: 1,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 16,
    color: COLORS.ink,
  },
  button: {
    backgroundColor: COLORS.accent,
    borderRadius: 12,
    paddingHorizontal: 16,
    justifyContent: 'center',
  },
  buttonPressed: { backgroundColor: COLORS.accentDeep },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  categories: {
    marginTop: 28,
    paddingHorizontal: 20,
  },
  sectionKicker: {
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    color: COLORS.accentSoft,
    marginBottom: 6,
  },
  sectionBrand: {
    fontFamily: 'serif',
    fontSize: 28,
    fontWeight: '600',
    color: COLORS.accentDeep,
    letterSpacing: -0.5,
  },
  categoryList: {
    marginTop: 14,
    borderTopWidth: 1,
    borderTopColor: COLORS.line,
  },
  categoryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.line,
  },
  categoryPressed: { paddingLeft: 8 },
  categoryLabel: {
    fontSize: 18,
    color: COLORS.ink,
  },
  categoryChevron: {
    fontSize: 22,
    color: COLORS.accentSoft,
  },
  resultsHead: {
    marginTop: 22,
    paddingHorizontal: 20,
    marginBottom: 8,
  },
  resultsTitle: {
    fontFamily: 'serif',
    fontSize: 26,
    fontWeight: '600',
    color: COLORS.accentDeep,
  },
  resultsMeta: {
    marginTop: 4,
    color: COLORS.inkSoft,
    fontSize: 14,
  },
  center: {
    alignItems: 'center',
    paddingVertical: 28,
    paddingHorizontal: 24,
    gap: 12,
  },
  muted: {
    color: COLORS.inkSoft,
    textAlign: 'center',
    lineHeight: 20,
  },
  mutedEmpty: {
    color: COLORS.inkSoft,
    paddingHorizontal: 20,
    marginVertical: 12,
  },
  errorBox: {
    marginHorizontal: 16,
    marginVertical: 12,
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: COLORS.accentSoft,
    backgroundColor: '#fff5f8',
  },
  errorText: { color: COLORS.danger, marginBottom: 6 },
  retry: { color: COLORS.accent, fontWeight: '700' },
  panel: {
    marginHorizontal: 16,
    marginTop: 8,
    marginBottom: 16,
    backgroundColor: COLORS.panel,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: COLORS.line,
    padding: 14,
  },
  panelTitle: {
    fontFamily: 'serif',
    fontSize: 20,
    fontWeight: '600',
    color: COLORS.accentDeep,
  },
  panelSub: {
    marginTop: 4,
    marginBottom: 10,
    color: COLORS.inkSoft,
    fontSize: 13,
  },
  byProduct: {
    marginHorizontal: 20,
    marginBottom: 10,
  },
  offerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: COLORS.line,
  },
  cheapestRow: { backgroundColor: COLORS.cheapestBg },
  offerMain: { flex: 1, paddingRight: 8 },
  offerStore: { fontWeight: '700', color: COLORS.ink },
  offerName: { color: COLORS.inkSoft, fontSize: 12, marginTop: 2 },
  offerRight: { alignItems: 'flex-end', gap: 2 },
  offerPrice: { fontWeight: '700', color: COLORS.accent },
  buyLink: {
    color: COLORS.accent,
    textDecorationLine: 'underline',
    fontSize: 12,
  },
  card: {
    marginHorizontal: 16,
    marginBottom: 12,
    backgroundColor: COLORS.panel,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: COLORS.line,
    padding: 14,
  },
  cardTop: { flexDirection: 'row', gap: 12 },
  image: {
    width: 72,
    height: 72,
    borderRadius: 12,
    backgroundColor: '#fff',
  },
  imagePlaceholder: { backgroundColor: COLORS.blush },
  cardBody: { flex: 1 },
  productName: { fontSize: 17, fontWeight: '600', color: COLORS.ink },
  size: { marginTop: 2, color: COLORS.inkSoft, fontSize: 13 },
  stores: { marginTop: 6, fontSize: 12, color: COLORS.accentDeep },
  priceCol: { alignItems: 'flex-end', minWidth: 88 },
  cheapestLabel: { fontSize: 12, color: COLORS.accent },
  price: { fontSize: 20, fontWeight: '700', color: COLORS.ink },
  buy: {
    marginTop: 4,
    color: COLORS.accent,
    textDecorationLine: 'underline',
    fontSize: 12,
  },
  offerTable: {
    marginTop: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.line,
    overflow: 'hidden',
  },
  miniOffer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: COLORS.line,
    gap: 8,
  },
  miniStore: { flex: 1, color: COLORS.ink, fontWeight: '600' },
  miniPrice: { fontWeight: '700', color: COLORS.accentDeep },
  backHome: {
    alignSelf: 'center',
    marginTop: 8,
    marginBottom: 20,
    paddingVertical: 10,
    paddingHorizontal: 16,
  },
  backHomeText: { color: COLORS.accent, fontWeight: '600', fontSize: 15 },
});

