import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Image,
  Linking,
  Pressable,
  SafeAreaView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  formatPkr,
  searchProducts,
  wakeApi,
  type SearchResult,
  type StoreOffer,
} from "./src/api";

export default function App() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [flat, setFlat] = useState<StoreOffer[]>([]);
  const [searched, setSearched] = useState(false);

  const onSearch = useCallback(async () => {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      await wakeApi();
      const data = await searchProducts(q);
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
  }, [query]);

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor="#F7F1E8" />
      <View style={styles.header}>
        <Text style={styles.brand}>PriceWise</Text>
        <Text style={styles.tagline}>Compare grocery prices across Pakistan</Text>
      </View>

      <View style={styles.searchRow}>
        <TextInput
          value={query}
          onChangeText={setQuery}
          placeholder='Search… e.g. "Surf Excel"'
          placeholderTextColor="#8A7F72"
          style={styles.input}
          returnKeyType="search"
          onSubmitEditing={onSearch}
        />
        <Pressable style={styles.button} onPress={onSearch} disabled={loading}>
          <Text style={styles.buttonText}>{loading ? "…" : "Compare"}</Text>
        </Pressable>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#7A1F2B" />
          <Text style={styles.muted}>Searching live stores…</Text>
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
        <Text style={styles.mutedEmpty}>No products found. Try another name.</Text>
      ) : null}

      <FlatList
        data={results}
        keyExtractor={(item, idx) =>
          `${item.variant_id || item.name}-${item.size_label}-${idx}`
        }
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          flat.length > 0 ? (
            <View style={styles.panel}>
              <Text style={styles.sectionTitle}>Cheapest store prices</Text>
              {flat.slice(0, 12).map((row, idx) => (
                <Pressable
                  key={`${row.retailer_id}-${row.url}-${idx}`}
                  style={styles.offerRow}
                  onPress={() => Linking.openURL(row.url)}
                >
                  <View style={styles.offerMain}>
                    <Text style={styles.offerStore}>{row.retailer_name}</Text>
                    <Text style={styles.offerName} numberOfLines={1}>
                      {row.product_name}
                    </Text>
                  </View>
                  <Text style={styles.offerPrice}>{formatPkr(row.price)}</Text>
                </Pressable>
              ))}
            </View>
          ) : null
        }
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View style={styles.cardTop}>
              {item.image_url ? (
                <Image source={{ uri: item.image_url }} style={styles.image} />
              ) : (
                <View style={[styles.image, styles.imagePlaceholder]} />
              )}
              <View style={styles.cardBody}>
                <Text style={styles.productName}>
                  {[item.brand, item.name].filter(Boolean).join(" ")}
                </Text>
                <Text style={styles.size}>{item.size_label}</Text>
                <Text style={styles.stores}>
                  {item.store_count} {item.store_count === 1 ? "store" : "stores"}
                </Text>
              </View>
              <View style={styles.priceCol}>
                <Text style={styles.cheapestLabel}>Cheapest</Text>
                <Text style={styles.price}>{formatPkr(item.cheapest.price)}</Text>
                <Pressable onPress={() => Linking.openURL(item.cheapest.url)}>
                  <Text style={styles.buy}>{item.cheapest.retailer_name}</Text>
                </Pressable>
              </View>
            </View>
            {(item.offers || []).slice(0, 5).map((offer) => (
              <Pressable
                key={`${offer.retailer_id}-${offer.url}`}
                style={styles.miniOffer}
                onPress={() => Linking.openURL(offer.url)}
              >
                <Text style={styles.miniStore}>{offer.retailer_name}</Text>
                <Text style={styles.miniPrice}>{formatPkr(offer.price)}</Text>
              </Pressable>
            ))}
          </View>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#F7F1E8" },
  header: { paddingHorizontal: 20, paddingTop: 12, paddingBottom: 8 },
  brand: {
    fontSize: 34,
    fontWeight: "700",
    color: "#5C1A22",
    letterSpacing: -0.5,
  },
  tagline: { marginTop: 4, color: "#8A7F72", fontSize: 14 },
  searchRow: {
    flexDirection: "row",
    gap: 8,
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  input: {
    flex: 1,
    backgroundColor: "#FFFDF9",
    borderWidth: 1,
    borderColor: "#E4D8C8",
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: "#2B241C",
  },
  button: {
    backgroundColor: "#7A1F2B",
    borderRadius: 14,
    paddingHorizontal: 16,
    justifyContent: "center",
  },
  buttonText: { color: "#FFF8F0", fontWeight: "600", fontSize: 15 },
  center: { alignItems: "center", paddingVertical: 24, gap: 10 },
  muted: { color: "#8A7F72" },
  mutedEmpty: { color: "#8A7F72", paddingHorizontal: 20, marginBottom: 8 },
  errorBox: {
    marginHorizontal: 16,
    marginBottom: 12,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#C45C5C",
    backgroundColor: "#FFF5F5",
  },
  errorText: { color: "#9B2C2C", marginBottom: 6 },
  retry: { color: "#7A1F2B", fontWeight: "600" },
  list: { paddingHorizontal: 16, paddingBottom: 32, gap: 12 },
  panel: {
    backgroundColor: "#FFFDF9",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#E4D8C8",
    padding: 14,
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#5C1A22",
    marginBottom: 10,
  },
  offerRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#E4D8C8",
  },
  offerMain: { flex: 1, paddingRight: 8 },
  offerStore: { fontWeight: "600", color: "#2B241C" },
  offerName: { color: "#8A7F72", fontSize: 12, marginTop: 2 },
  offerPrice: { fontWeight: "700", color: "#7A1F2B" },
  card: {
    backgroundColor: "#FFFDF9",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#E4D8C8",
    padding: 14,
    marginBottom: 12,
  },
  cardTop: { flexDirection: "row", gap: 10 },
  image: {
    width: 64,
    height: 64,
    borderRadius: 10,
    backgroundColor: "#fff",
  },
  imagePlaceholder: { backgroundColor: "#EFE7DC" },
  cardBody: { flex: 1 },
  productName: { fontSize: 16, fontWeight: "600", color: "#2B241C" },
  size: { marginTop: 2, color: "#8A7F72", fontSize: 13 },
  stores: { marginTop: 6, fontSize: 12, color: "#5C1A22" },
  priceCol: { alignItems: "flex-end", minWidth: 88 },
  cheapestLabel: { fontSize: 11, color: "#7A1F2B" },
  price: { fontSize: 18, fontWeight: "700", color: "#2B241C" },
  buy: {
    marginTop: 4,
    color: "#7A1F2B",
    textDecorationLine: "underline",
    fontSize: 12,
  },
  miniOffer: {
    marginTop: 8,
    flexDirection: "row",
    justifyContent: "space-between",
    paddingTop: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: "#E4D8C8",
  },
  miniStore: { color: "#2B241C" },
  miniPrice: { fontWeight: "600", color: "#5C1A22" },
});
