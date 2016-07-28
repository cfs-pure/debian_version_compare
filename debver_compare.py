import re
import sys

from debian.debian_support import BaseVersion as _BaseVersion

class BaseVersion(_BaseVersion):
    def _compare(self, other):
        def cmp_part(a, b):
            """ Compare a part of a full Debian version string. """

            def normalize(ver_str):
                """ Pull apart a Debian version fragment into a series of
                    either numeric or non-integer tokens.  For numeric tokens,
                    those are then converted into actual integers.
                """
                # Deal with optional parts.
                ver_str = "0" if not ver_str else ver_str
                return [int(part) if part.isdigit() else part for part in re.findall(r"[^\d]+|\d+", ver_str)]

            # Magical Debian character sort order and the less magical lambda
            # that uses it to generate the custom sort order.
            order = '~:' \
                    '0123456789' \
                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ' \
                    'abcdefghijklmnopqrstuvwxyz' \
                    '-+.'
            key = lambda word: [order.index(c) for c in word]

            # Tokenize and backfill the values being compared so they are of
            # the same length.
            a = normalize(a)
            b = normalize(b)
            values_len_max = max(len(a), len(b))
            for value in [a, b]:
                if len(value) < values_len_max:
                    value.extend([0] * (values_len_max - len(value)))

            # Compare all of the tokens until a difference is found.
            cmp_result = 0
            for idx in range(len(a)):
                cmp_values = [a[idx], b[idx]]
                if all(isinstance(value, int) for value in cmp_values):
                    # If both tokens are integers, it's easy.
                    cmp_result = cmp(*cmp_values)
                else:
                    # Otherwise, if either happens to be an integer put it
                    # through the grinder as a string.
                    cmp_values = [str(value) for value in cmp_values]
                    if len(set(cmp_values)) != 1:
                        if cmp_values[0] is sorted(cmp_values, key=key)[0]:
                            cmp_result = -1
                        else:
                            cmp_result = 1
                if cmp_result != 0:
                    break
            return cmp_result

        # Types changed while you wait!
        if isinstance(other, basestring):
            other = BaseVersion(other)
        elif not isinstance(other, BaseVersion):
            raise TypeError('Can only compare BaseVersion objects!')

        # First, compare epochs.  If there isn't one treat it as 0
        epochs = [0 if self.epoch is None else int(self.epoch),
                  0 if other.epoch is None else int(other.epoch)]
        epoch = cmp(*epochs)
        if epoch:
            return epoch

        # Next, compare the upstream_version part.
        upstream = cmp_part(self.upstream_version, other.upstream_version)
        if upstream:
            return upstream

        # Lastly, compare debian_version.  Even if this is not part of the
        # full version string, it will be compared as "0".
        debian = cmp_part(self.debian_version, other.debian_version)
        return debian

test_data = [(('7.6p2-4', '7.6-0'), 1),
             (('1.0.3-3', '1.0-1'), 1),
             (('1.3', '1.2.2-2'), 1),
             (('1.3', '1.2.2'), 1),
             (('1:0.4', '10.3'), 1),
             (('1:1.25-4', '1:1.25-8'), -1),
             (('0:1.18.36', '1.18.36'), 0),
             (('1.18.36', '1.18.35'), 1),
             (('0:1.18.36', '1.18.35'), 1),
             (('9:1.18.36:5.4-20', '10:0.5.1-22'), -1),
             (('9:1.18.36:5.4-20', '9:1.18.36:5.5-1'), -1),
             (('9:1.18.36:5.4-20', '9:1.18.37:4.3-22'), -1),
             (('1.18.36-0.17.35-18', '1.18.36-19'), 1),
             (('1:1.2.13-3', '1:1.2.13-3.1'), -1),
             (('2.0.7pre1-4', '2.0.7r-1'), -1),
             (('0-pre', '0-pre'), 0),
             (('0-pre', '0-pree'), -1),
             (('1.1.6r2-2', '1.1.6r-1'), 1),
             (('2.6b2-1', '2.6b-2'), 1),
             (('98.1p5-1', '98.1-pre2-b6-2'), -1),
             (('0.4a6-2', '0.4-1'), 1),
             (('1:3.0.5-2', '1:3.0.5.1'), -1),
             (('3.0~rc1-1', '3.0-1'), -1),
             (('1.0', '1.0-0'), 0),
             (('0.2', '1.0-0'), -1),
             (('1.0', '1.0-0+b1'), -1),
             (('1.0', '1.0-0~'), 1),
             (('0:0-0-0', '0-0'), 1),
             (('0', '0'), 0),
             (('0', '00'), 0),
             (('1.2.3', '1.2.3'), 0),
             (('4.4.3-2', '4.4.3-2'), 0),
             (('1:2ab:5', '1:2ab:5'), 0),
             (('7:1-a:b-5', '7:1-a:b-5'), 0),
             (('57:1.2.3abYZ+~-4-5', '57:1.2.3abYZ+~-4-5'), 0),
             (('1.2.3', '0:1.2.3'), 0),
             (('1.2.3', '1.2.3-0'), 0),
             (('009', '9'), 0),
             (('009ab5', '9ab5'), 0),
             (('1.2.3', '1.2.3-1'), -1),
             (('1.2.3', '1.2.4'), -1),
             (('1.2.4', '1.2.3'), 1),
             (('1.2.24', '1.2.3'), 1),
             (('0.10.0', '0.8.7'), 1),
             (('3.2', '2.3'), 1),
             (('1.3.2a', '1.3.2'), 1),
             (('0.5.0~git', '0.5.0~git2'), -1),
             (('2a', '21'), -1),
             (('1.3.2a', '1.3.2b'), -1),
             (('1:1.2.3', '1.2.4'), 1),
             (('1:1.2.3', '1:1.2.4'), -1),
             (('1.2a+~bCd3', '1.2a++'), -1),
             (('1.2a+~bCd3', '1.2a+~'), 1),
             (('5:2', '304-2'), 1),
             (('5:2', '304:2'), -1),
             (('25:2', '3:2'), 1),
             (('1:2:123', '1:12:3'), -1),
             (('1.2-5', '1.2-3-5'), -1),
             (('5.10.0', '5.005'), 1),
             (('3a9.8', '3.10.2'), -1),
             (('3a9.8', '3~10'), 1),
             (('1.4+OOo3.0.0~', '1.4+OOo3.0.0-4'), -1),
             (('2.4.7-1', '2.4.7-z'), -1),
             (('1.002-1+b2', '1.00'), 1)
            ]

def main():
    fail = 0
    fail_tmpl = "FAIL {} expected: {}, actual: {}"
    for test in test_data:
        test_vals, expected_res = test
        a, b = test_vals
        actual_res = cmp(BaseVersion(a), BaseVersion(b))
        if expected_res != actual_res:
            fail = 1
            fail_msg = fail_tmpl.format(test_vals, expected_res, actual_res)
            print >> sys.stderr, fail_msg

if __name__ == '__main__':
    sys.exit(main())
