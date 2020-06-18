# 画准确率的图

import matplotlib.pyplot as plt
acc = {1: 0.12800898308653239, 2: 0.22689121489614827, 3: 0.4002071684299449, 4: 0.47783104466292897, 5: 0.5343642317121257, 6: 0.5687277358753408, 7: 0.5975703382558822, 8: 0.6198884758364313, 9: 0.6401707121899173, 10: 0.6581240565390422, 11: 0.675235542560104, 12: 0.6891277791351087, 13: 0.6947267726892263, 14: 0.6996871741397289, 15: 0.7069425287356322}
accs = acc.values()

x = range(1, 16)

plt.plot(x, accs)
plt.show()