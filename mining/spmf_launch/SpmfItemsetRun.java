import ca.pfv.spmf.algorithms.frequentpatterns.apriori.AlgoApriori;
import ca.pfv.spmf.algorithms.frequentpatterns.eclat.AlgoEclat;
import ca.pfv.spmf.algorithms.frequentpatterns.fpgrowth.AlgoFPGrowth;
import ca.pfv.spmf.input.transaction_database_list_integers.TransactionDatabase;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;

/**
 * Calls the SPMF 2.12.1 itemset miners.
 *
 * This build opens its input with ClassLoader.getResourceAsStream, so the
 * dataset file must sit at the root of a classpath entry. The argument is the
 * file name, not a filesystem path. The output argument is a normal file path.
 */
public class SpmfItemsetRun {
    public static void main(String[] args) throws Exception {
        if (args.length != 4) {
            throw new IllegalArgumentException(
                "Usage: SpmfItemsetRun <Apriori|FPGrowth|Eclat> <classpath-input> <output> <absolute-min-support>");
        }
        String algorithm = args[0];
        String input = args[1];
        String output = args[2];
        int absoluteMinSupport = Integer.parseInt(args[3]);
        if (absoluteMinSupport < 1) {
            throw new IllegalArgumentException("absolute minimum support must be at least 1");
        }

        int transactionCount = countTransactions(input);
        double minsup = ratioForAbsoluteSupport(absoluteMinSupport, transactionCount);
        int interpreted = (int) Math.ceil(minsup * transactionCount);
        if (interpreted != absoluteMinSupport) {
            throw new IllegalStateException(
                "SPMF would keep support " + interpreted + " instead of " + absoluteMinSupport);
        }

        long start = System.nanoTime();
        if ("Apriori".equals(algorithm)) {
            new AlgoApriori().runAlgorithm(minsup, input, output);
        } else if ("FPGrowth".equals(algorithm)) {
            new AlgoFPGrowth().runAlgorithm(input, output, minsup);
        } else if ("Eclat".equals(algorithm)) {
            TransactionDatabase database = new TransactionDatabase();
            database.loadFile(input);
            if (database.size() != transactionCount) {
                throw new IllegalStateException(
                    "Eclat loaded " + database.size() + " transactions; the file has " + transactionCount);
            }
            new AlgoEclat().runAlgorithm(output, database, minsup, false);
        } else {
            throw new IllegalArgumentException("Unknown algorithm: " + algorithm);
        }
        long elapsedNs = System.nanoTime() - start;

        System.out.println("ELAPSED_NS " + elapsedNs);
        System.out.println("TRANSACTIONS " + transactionCount);
        System.out.println("MINSUP_RATIO " + minsup);
        System.out.println("MINSUP_ABSOLUTE " + interpreted);
    }

    static int countTransactions(String input) throws Exception {
        InputStream stream = SpmfItemsetRun.class.getClassLoader().getResourceAsStream(input);
        if (stream == null) {
            throw new IllegalStateException(
                "Classpath does not contain " + input + ". Put that file in a classpath directory.");
        }
        BufferedReader reader = new BufferedReader(new InputStreamReader(stream, "UTF-8"));
        int count = 0;
        try {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isEmpty() || line.charAt(0) == '#' || line.charAt(0) == '%' || line.charAt(0) == '@') {
                    continue;
                }
                count++;
            }
        } finally {
            reader.close();
        }
        if (count == 0) {
            throw new IllegalStateException("No transactions in " + input);
        }
        return count;
    }

    /**
     * SPMF converts a ratio with Math.ceil(ratio * n). Nudge the double until
     * that conversion is exactly the absolute count, so a value such as 2/63
     * cannot fall on the wrong side of an integer.
     */
    static double ratioForAbsoluteSupport(int absolute, int transactionCount) {
        double ratio = absolute / (double) transactionCount;
        int guard = 0;
        while ((int) Math.ceil(ratio * transactionCount) > absolute && guard < 10000) {
            ratio = Math.nextDown(ratio);
            guard++;
        }
        while ((int) Math.ceil(ratio * transactionCount) < absolute && guard < 20000) {
            ratio = Math.nextUp(ratio);
            guard++;
        }
        return ratio;
    }
}
