# AxonForge Risk Yönetim Motoru (Risk Engine)

Risk Engine, portföy düzeyinde maruz kalınan riskleri ve uç olay olasılıklarını ölçer.

## 1. Riske Maruz Değer (Value at Risk - VaR) Modellemesi

VaR, belirli bir güven düzeyinde ($\alpha$) ve belirli bir zaman ufkunda portföyün uğrayabileceği maksimum kaybı temsil eder. AxonForge üç farklı VaR hesaplama yöntemini destekler:

1.  **Parametrik (Parametric / Variance-Covariance) VaR:**
    Getirilerin normal dağıldığı varsayımı altında hesaplanır:
    $$VaR_{\alpha} = - (\mu_p - Z_{\alpha} \sigma_p)$$
    Burada $\mu_p$ portföyün ortalama günlük getirisi, $\sigma_p$ standart sapması (volatilitesi) ve $Z_{\alpha}$ standart normal dağılımın $\alpha$ güven düzeyindeki kritik değeridir (örn: %95 için 1.645).

2.  **Tarihsel (Historical Simulation) VaR:**
    Herhangi bir parametrik dağılım varsayımı olmaksızın, portföyün geçmiş günlük getirilerinin yüzdelik dilimi (percentile) alınarak hesaplanır:
    $$VaR_{\alpha} = - \text{Percentile}(\text{Getiriler}, 1 - \alpha)$$

3.  **Monte Carlo VaR:**
    Varlıkların tarihsel ortalama getirileri ve kovaryans matrisi ($\Sigma$) kullanılarak geleceğe yönelik 5,000 simüle edilmiş getiri yolu türetilir. Bu yolların portföy ağırlıklarıyla çarpılması sonucu elde edilen dağılımın $1-\alpha$ dilimi hesaplanır.

## 2. Beklenen Kayıp (Expected Shortfall - ES / CVaR)

VaR eşiğinin aşıldığı durumlardaki ortalama kaybı (kuyruk riskini) temsil eder:
$$ES_{\alpha} = - E[R_p \mid R_p \le -VaR_{\alpha}]$$
ES, portföy getirilerinin normal olmayan uç olay dağılımlarını (fat-tails) yakalamak için VaR'a kıyasla daha güvenilir bir göstergedir.

## 3. Performans Rasyoları

*   **Sharpe Oranı:** Portföyün birim risk başına elde ettiği aşırı getiridir.
*   **Sortino Oranı:** Sadece negatif getirilerin standart sapmasını (Downside Deviation) kullanarak hesaplama yapar.
*   **Max Drawdown:** Portföy değerinin ulaştığı en yüksek zirveden yaşadığı en derin düşüş yüzdesidir.
